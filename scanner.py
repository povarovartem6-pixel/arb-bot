import asyncio
import ccxt.async_support as ccxt
from config import (DEFAULT_TAKER_FEE, MIN_24H_VOLUME_USDT,
                    MAX_SYMBOLS_PER_SCAN, EXCHANGE_TIMEOUT,
                    SUPPORTED_EXCHANGES)

def _get_fee(exchange):
    try:
        taker = exchange.fees["trading"]["taker"]
        return taker if taker else DEFAULT_TAKER_FEE
    except Exception:
        return DEFAULT_TAKER_FEE

async def _safe_fetch_tickers(exchange, symbols=None):
    try:
        return await exchange.fetch_tickers(symbols)
    except Exception:
        return {}

async def _check_liquidity(exchange, symbol, trade_size, side):
    try:
        ob = await exchange.fetch_order_book(symbol, limit=5)
        levels = ob.get(side, [])
        available = sum(price * amount for price, amount in levels[:5])
        return available >= trade_size
    except Exception:
        return True

async def _scan_one_target(source, source_id, source_fee,
                           common_symbols, target_id, threshold,
                           trade_size, min_volume):
    results = []
    try:
        target = getattr(ccxt, target_id)({
            "enableRateLimit": True,
            "timeout": EXCHANGE_TIMEOUT * 1000,
        })
    except Exception:
        return results

    try:
        await target.load_markets()
        common = list(set(common_symbols) & set(target.symbols))[:MAX_SYMBOLS_PER_SCAN]
        if not common:
            return results

        src_tickers = await _safe_fetch_tickers(source, common)
        tgt_tickers = await _safe_fetch_tickers(target, common)
        target_fee = _get_fee(target)
        total_fee_pct = (source_fee + target_fee) * 100

        for symbol in common:
            s_t = src_tickers.get(symbol)
            t_t = tgt_tickers.get(symbol)
            if not s_t or not t_t:
                continue

            quote_vol = t_t.get("quoteVolume") or s_t.get("quoteVolume") or 0
            if quote_vol < min_volume:
                continue

            s_ask = s_t.get("ask") or s_t.get("last")
            t_bid = t_t.get("bid") or t_t.get("last")
            if not s_ask or not t_bid:
                continue

            gross = (t_bid - s_ask) / s_ask * 100
            if gross < threshold:
                continue

            net = gross - total_fee_pct
            if net <= 0:
                continue

            if not await _check_liquidity(source, symbol, trade_size, "asks"):
                continue
            if not await _check_liquidity(target, symbol, trade_size, "bids"):
                continue

            results.append({
                "symbol": symbol,
                "source": source_id,
                "target": target_id,
                "s_price": s_ask,
                "t_price": t_bid,
                "gross": gross,
                "net": net,
            })
    except Exception:
        pass
    finally:
        try:
            await target.close()
        except Exception:
            pass

    return results

async def scan_all(source_id, threshold, trade_size,
                   min_volume=MIN_24H_VOLUME_USDT,
                   progress_cb=None):
    source = getattr(ccxt, source_id)({
        "enableRateLimit": True,
        "timeout": EXCHANGE_TIMEOUT * 1000,
    })
    all_results = []

    try:
        await source.load_markets()
        source_symbols = {
            s for s in source.symbols
            if s.endswith("/USDT") or s.endswith("/USD") or s.endswith("/BTC")
        }
        source_fee = _get_fee(source)

        target_ids = [ex for ex in SUPPORTED_EXCHANGES if ex != source_id]

        sem = asyncio.Semaphore(4)

        async def worker(tid):
            async with sem:
                r = await _scan_one_target(
                    source, source_id, source_fee,
                    source_symbols, tid, threshold,
                    trade_size, min_volume
                )
                return tid, r

        tasks = [asyncio.create_task(worker(tid)) for tid in target_ids]
        done = 0
        total = len(tasks)

        for coro in asyncio.as_completed(tasks):
            tid, r = await coro
            done += 1
            if r:
                all_results.extend(r)
            if progress_cb:
                try:
                    await progress_cb(done, total, len(all_results))
                except Exception:
                    pass
    finally:
        await source.close()

    return sorted(all_results, key=lambda x: -x["net"])
