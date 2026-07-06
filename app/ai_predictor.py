import sqlite3
import os
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from app.weather_service import get_weather_forecast, get_historical_weather

def get_db_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def predict_customer_refills(db_path):
    """
    Analyzes historical orders for each customer to predict their next refill date
    and refill urgency status.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Query all active customers
    cursor.execute("SELECT id, full_name, phone, address FROM customers WHERE is_active = 1")
    customers = cursor.fetchall()
    
    predictions = []
    today = datetime.now().date()
    
    for customer in customers:
        customer_id = customer['id']
        
        # Get all completed orders for this customer ordered by date
        cursor.execute(
            "SELECT order_date FROM orders WHERE customer_id = ? AND status = 'completed' ORDER BY order_date ASC",
            (customer_id,)
        )
        orders = cursor.fetchall()
        
        if not orders:
            predictions.append({
                'customer_id': customer_id,
                'name': customer['full_name'],
                'phone': customer['phone'] or 'N/A',
                'address': customer['address'] or 'N/A',
                'last_order_date': 'None',
                'predicted_refill_date': 'N/A',
                'days_since_last': -1,
                'status': 'No History',
                'avg_interval': 7.0
            })
            continue
            
        # Parse order dates
        order_dates = []
        for o in orders:
            dt_str = o['order_date']
            try:
                # Handle SQLite datetime strings (strip timezone or fractional seconds if needed)
                dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                order_dates.append(dt.date())
            except ValueError:
                # Handle simple date strings or other formats
                try:
                    dt = datetime.strptime(dt_str[:10], '%Y-%m-%d').date()
                    order_dates.append(dt)
                except Exception:
                    pass
                    
        # Remove duplicate dates (multiple orders on the same day)
        order_dates = sorted(list(set(order_dates)))
        
        last_order_date = order_dates[-1]
        days_since_last = (today - last_order_date).days
        
        # Calculate average interval between orders
        if len(order_dates) > 1:
            intervals = []
            for i in range(1, len(order_dates)):
                intervals.append((order_dates[i] - order_dates[i-1]).days)
            avg_interval = float(np.mean(intervals))
            # Put lower/upper bounds to make realistic
            avg_interval = max(3.0, min(avg_interval, 30.0))
        else:
            # Default to 7 days for single orders
            avg_interval = 7.0
            
        # Predict next refill date
        predicted_refill_date = last_order_date + timedelta(days=round(avg_interval))
        days_until_refill = (predicted_refill_date - today).days
        
        # Determine status classification
        if days_until_refill <= 0:
            status = 'Due Now'
        elif days_until_refill <= 2:
            status = 'Due Soon'
        else:
            status = 'Okay'
            
        predictions.append({
            'customer_id': customer_id,
            'name': customer['full_name'],
            'phone': customer['phone'] or 'N/A',
            'address': customer['address'] or 'N/A',
            'last_order_date': last_order_date.strftime('%Y-%m-%d'),
            'predicted_refill_date': predicted_refill_date.strftime('%Y-%m-%d'),
            'days_since_last': days_since_last,
            'status': status,
            'avg_interval': round(avg_interval, 1)
        })
        
    conn.close()
    return predictions

def forecast_water_demand(db_path):
    """
    Predicts the daily demand of water containers (in units) for the next 7 days
    using historical order history and weather forecasts for Meycauayan.
    """
    conn = get_db_connection(db_path)
    
    # Query daily completed/confirmed orders and sum their item quantities
    query = """
        SELECT DATE(o.order_date) as order_day, SUM(oi.quantity) as total_qty
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        WHERE o.status IN ('completed', 'confirmed')
        GROUP BY order_day
        ORDER BY order_day ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Fetch weather forecast for next 7 days
    weather_data = get_weather_forecast()
    forecast_list = weather_data['daily_forecast']
    
    # Check if we have enough historical data to train a Scikit-Learn model
    if len(df) < 5:
        # Fallback to pure rule-based / moving average forecasting if data is too sparse
        print("Sparse sales history. Using moving average fallback for forecasting.")
        avg_daily_sales = df['total_qty'].mean() if not df.empty else 10.0
        # If mean is nan, set to 10
        if np.isnan(avg_daily_sales):
            avg_daily_sales = 10.0
            
        forecast_results = []
        for idx, fc in enumerate(forecast_list):
            fc_date = datetime.strptime(fc['date'], '%Y-%m-%d')
            day_of_week = fc_date.weekday()
            
            # Simple seasonal adjustment:
            # - Weekends (Saturday=5, Sunday=6) have slightly lower commercial sales (-15%)
            # - Hotter days (+33C) increase demand (+10% for every degree above 31C)
            temp_mult = 1.0 + max(0.0, (fc['max_temp'] - 31.0) * 0.08)
            day_mult = 0.85 if day_of_week in [5, 6] else 1.05
            
            predicted_val = max(1.0, round(avg_daily_sales * day_mult * temp_mult, 1))
            
            forecast_results.append({
                'date': fc['date'],
                'day_name': fc_date.strftime('%A'),
                'max_temp': fc['max_temp'],
                'precipitation': fc['precipitation'],
                'predicted_demand': predicted_val
            })
        return forecast_results

    # If we have enough history, train the machine learning regression model
    df['order_day'] = pd.to_datetime(df['order_day'])
    df = df.set_index('order_day').asfreq('D', fill_value=0) # Resample to daily frequency, filling gaps with 0
    
    # Get historical weather for each date in our index
    dates_list = [d.strftime('%Y-%m-%d') for d in df.index]
    hist_weather = get_historical_weather(dates_list)
    
    # Add weather features to historical dataframe
    df['max_temp'] = [hist_weather[d]['max_temp'] for d in dates_list]
    df['precipitation'] = [hist_weather[d]['precipitation'] for d in dates_list]
    
    # Calendar features
    df['day_of_week'] = df.index.dayofweek
    df['day_of_month'] = df.index.day
    
    # Lag feature: rolling 3-day average of sales
    df['rolling_sales'] = df['total_qty'].shift(1).rolling(window=3, min_periods=1).mean().fillna(df['total_qty'].mean())
    
    # Train scikit-learn LinearRegression model
    from sklearn.linear_model import LinearRegression
    
    X = df[['max_temp', 'precipitation', 'day_of_week', 'rolling_sales']]
    y = df['total_qty']
    
    model = LinearRegression()
    model.fit(X, y)
    
    # Prepare forecast dates
    forecast_results = []
    recent_sales = list(df['total_qty'].values[-3:]) # Start with the last 3 days of real sales
    
    for fc in forecast_list:
        fc_date = datetime.strptime(fc['date'], '%Y-%m-%d')
        day_of_week = fc_date.weekday()
        
        # Calculate rolling sales feature based on recent predictions or real values
        rolling_val = np.mean(recent_sales[-3:]) if recent_sales else df['total_qty'].mean()
        
        # Features DataFrame with correct column names to avoid warnings
        features = pd.DataFrame([[
            fc['max_temp'],
            fc['precipitation'],
            day_of_week,
            rolling_val
        ]], columns=['max_temp', 'precipitation', 'day_of_week', 'rolling_sales'])
        
        # Predict
        predicted_val = model.predict(features)[0]
        # Restrict to non-negative
        predicted_val = max(1.0, round(predicted_val, 1))
        
        forecast_results.append({
            'date': fc['date'],
            'day_name': fc_date.strftime('%A'),
            'max_temp': fc['max_temp'],
            'precipitation': fc['precipitation'],
            'predicted_demand': predicted_val
        })
        
        # Append prediction to recent sales list to feed the rolling window for the next forecast day
        recent_sales.append(predicted_val)
        
    return forecast_results
