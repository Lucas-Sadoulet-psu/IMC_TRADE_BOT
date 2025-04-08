import json
from typing import Dict, List, Tuple
from datamodel import OrderDepth, TradingState, Order


class Trader:
    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        """
        Executes the trading strategy on every tick.
        Maintains a history of mid-prices for each product and generates a BUY order when the short SMA crosses above the long SMA.
        Returns:
          - result: Dict mapping product to list of orders to be sent.
          - conversions: An integer conversion factor (here set to 1).
          - traderData: A persistent string (in JSON) used to store state between ticks.
        """
        result = {}

        # Load existing price history from the persistent trader data (if any)
        try:
            price_history = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            price_history = {}

        # Loop over every product that has an order depth
        for product in state.order_depths.keys():
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            # Compute a representative price (mid-price) from order book data.
            # Use both sides of the book if available.
            if order_depth.buy_orders and order_depth.sell_orders:
                best_bid = max(order_depth.buy_orders.keys())
                best_ask = min(order_depth.sell_orders.keys())
                mid_price = (best_bid + best_ask) / 2.0
            elif order_depth.buy_orders:
                mid_price = max(order_depth.buy_orders.keys())
            elif order_depth.sell_orders:
                mid_price = min(order_depth.sell_orders.keys())
            else:
                # If no orders exist, skip this product.
                continue

            # Update persistent price history for this product.
            # The history is stored as a list of mid prices.
            if product not in price_history:
                price_history[product] = []
            price_history[product].append(mid_price)

            # Define the window sizes for the short and long SMAs.
            short_window = 3  # e.g., last 3 ticks
            long_window = 6   # e.g., last 6 ticks

            # We require enough data for both the current and previous SMA calculations.
            if len(price_history[product]) >= long_window + 1:
                # Calculate current SMAs using the most recent data
                sma_short = sum(price_history[product][-short_window:]) / short_window
                sma_long = sum(price_history[product][-long_window:]) / long_window

                # Calculate previous SMAs (using the data set from one tick earlier)
                sma_short_prev = sum(price_history[product][-short_window - 1:-1]) / short_window
                sma_long_prev = sum(price_history[product][-long_window - 1:-1]) / long_window

                # Check for a crossover from below: previous short <= previous long and now short > long.
                if sma_short_prev <= sma_long_prev and sma_short > sma_long:
                    # A bullish crossover is detected.
                    # Generate a BUY order only if there is a sell order (to get a price quote).
                    if order_depth.sell_orders:
                        best_ask = min(order_depth.sell_orders.keys())
                        order_quantity = 10  # Here you could use a fixed quantity or some position management logic.
                        orders.append(Order(product, best_ask, order_quantity))
                        print(f"BUY {order_quantity}x {product} at {best_ask} (SMA crossover: {sma_short_prev}->{sma_short} vs {sma_long_prev}->{sma_long})")

            # Add orders for this product (if any) to the result.
            result[product] = orders

        # Save the updated price history into traderData (serialized as JSON)
        traderData = json.dumps(price_history)
        conversions = 1

        return result, conversions, traderData
