import numpy as np
import pandas as pd
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    # Fallback implementation if TA-Lib is not available
    class talib:
        @staticmethod
        def RSI(series, timeperiod=14):
            delta = series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=timeperiod).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=timeperiod).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        
        @staticmethod
        def MACD(series, fastperiod=12, slowperiod=26, signalperiod=9):
            ema_fast = series.ewm(span=fastperiod).mean()
            ema_slow = series.ewm(span=slowperiod).mean()
            macd = ema_fast - ema_slow
            signal = macd.ewm(span=signalperiod).mean()
            histogram = macd - signal
            return macd, signal, histogram
        
        @staticmethod
        def EMA(series, timeperiod=30):
            return series.ewm(span=timeperiod).mean()
        
        @staticmethod
        def SMA(series, timeperiod=30):
            return series.rolling(window=timeperiod).mean()

import logging
import os
from typing import Dict

logger = logging.getLogger(__name__)

# Try to import freqtrade, make it optional
try:
    from freqtrade.strategy import IStrategy
    from freqtrade.strategy import DecimalParameter, IntParameter
    FREQTRADE_AVAILABLE = True
except ImportError:
    FREQTRADE_AVAILABLE = False
    # Create a basic IStrategy class if not available
    class IStrategy:
        def __init__(self, config=None):
            self.config = config or {}
    
    class IntParameter:
        def __init__(self, *args, **kwargs):
            if len(args) >= 3:
                self.value = args[2] if args[2] else 14
            elif 'default' in kwargs:
                self.value = kwargs['default']
            else:
                self.value = 14
    
    class DecimalParameter:
        def __init__(self, *args, **kwargs):
            if len(args) >= 3:
                self.value = args[2] if args[2] else 0.02
            elif 'default' in kwargs:
                self.value = kwargs['default']
            else:
                self.value = 0.02

class AdvancedTradingStrategy(IStrategy if FREQTRADE_AVAILABLE else object):
    INTERFACE_VERSION = 3 if FREQTRADE_AVAILABLE else 1
    timeframe = '15m'
    can_short = True
    
    minimal_roi = {"0": 0.06, "30": 0.04, "60": 0.02, "120": 0.01}
    stoploss = -0.03
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.025
    trailing_only_offset_is_reached = True
    process_only_new_candles = False
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 200
    
    rsi_period = IntParameter(10, 30, default=14, space="buy")
    rsi_oversold = IntParameter(20, 40, default=30, space="buy")
    rsi_overbought = IntParameter(60, 80, default=70, space="sell")
    risk_per_trade = DecimalParameter(0.005, 0.03, default=0.01, space="buy")
    
    def __init__(self, config: dict):
        if FREQTRADE_AVAILABLE:
            super().__init__(config)
        else:
            self.config = config or {}
            self.performance_history = []
        
        try:
            from api.deepseek_client import DeepSeekClient
            from utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            # Try to get API key from config
            api_key = config_manager.get_api_key('openrouter', 'api_key')
            if api_key:
                self.deepseek_client = DeepSeekClient(api_key)
            else:
                self.deepseek_client = None
            # Load analysis and symbol settings
            try:
                self.analysis_cfg = (config_manager.strategy_config or {}).get('analysis', {})
            except Exception:
                self.analysis_cfg = {}
            try:
                symbols_cfg = (config_manager.strategy_config or {}).get('symbols', {})
                self.perpetual_whitelist = symbols_cfg.get('perpetual_whitelist', [])
            except Exception:
                self.perpetual_whitelist = []
        except (ImportError, AttributeError) as e:
            logger.warning(f"DeepSeek client not available: {e}")
            self.deepseek_client = None
            self.analysis_cfg = {}
            self.perpetual_whitelist = []
    
    def informative_pairs(self):
        if FREQTRADE_AVAILABLE and hasattr(self, 'dp'):
            pairs = self.dp.current_whitelist()
            informative_pairs = []
            for pair in pairs:
                informative_pairs.append((pair, '30m'))
                informative_pairs.append((pair, '1h'))
            return informative_pairs
        return []
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe['rsi'] = talib.RSI(dataframe['close'], timeperiod=self.rsi_period.value)
        macd_result = talib.MACD(dataframe['close'])
        
        # Handle MACD tuple return
        if isinstance(macd_result, tuple):
            macd, macd_signal, macd_hist = macd_result
        else:
            macd = macd_result
            macd_signal = macd
            macd_hist = macd
        
        dataframe['macd'] = macd
        dataframe['macd_signal'] = macd_signal
        dataframe['ema_12'] = talib.EMA(dataframe['close'], timeperiod=12)
        dataframe['ema_26'] = talib.EMA(dataframe['close'], timeperiod=26)
        dataframe['sma_50'] = talib.SMA(dataframe['close'], timeperiod=50)
        dataframe['ema_200'] = talib.EMA(dataframe['close'], timeperiod=200)
        dataframe['volume_sma'] = talib.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']
        
        # Micro volatility and volume strength
        try:
            n = int(self.analysis_cfg.get('micro_volatility_candles', 10))
        except Exception:
            n = 10
        try:
            dataframe['return_pct'] = dataframe['close'].pct_change() * 100.0
        except Exception:
            dataframe['return_pct'] = 0.0
        try:
            dataframe['micro_vol_std'] = dataframe['return_pct'].rolling(window=max(n, 2)).std().abs()
        except Exception:
            dataframe['micro_vol_std'] = 0.0
        try:
            weak_thr = float(self.analysis_cfg.get('volume_strength_thresholds', {}).get('weak', 0.9))
        except Exception:
            weak_thr = 0.9
        try:
            strong_thr = float(self.analysis_cfg.get('volume_strength_thresholds', {}).get('strong', 1.2))
        except Exception:
            strong_thr = 1.2
        dataframe['volume_strength'] = dataframe['volume_ratio']
        dataframe['volume_signal'] = np.where(dataframe['volume_strength'] >= strong_thr, 1,
                                              np.where(dataframe['volume_strength'] <= weak_thr, -1, 0))

        # ATR for dynamic risk management
        try:
            if TALIB_AVAILABLE:
                import talib as ta
                dataframe['atr'] = ta.ATR(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)
            else:
                tr1 = (dataframe['high'] - dataframe['low']).abs()
                tr2 = (dataframe['high'] - dataframe['close'].shift(1)).abs()
                tr3 = (dataframe['low'] - dataframe['close'].shift(1)).abs()
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                dataframe['atr'] = tr.rolling(window=14).mean()
        except Exception:
            dataframe['atr'] = dataframe['close'].rolling(window=14).std()
        
        # AI analysis if client is available
        if self.deepseek_client and not dataframe.empty:
            try:
                market_data = {
                    'close': float(dataframe['close'].iloc[-1]) if len(dataframe) > 0 else 0,
                    'rsi': float(dataframe['rsi'].iloc[-1]) if not dataframe['rsi'].empty else 50,
                    'macd': float(dataframe['macd'].iloc[-1]) if not dataframe['macd'].empty else 0
                }
                
                ai_analysis = self.deepseek_client.analyze_market(market_data)
                last_index = dataframe.index[-1]
                dataframe.at[last_index, 'ai_action'] = ai_analysis.get('action', 'HOLD')
                dataframe.at[last_index, 'ai_confidence'] = ai_analysis.get('confidence', 0.0)
            except Exception as e:
                logger.warning(f"AI analysis failed: {e}")
                dataframe['ai_action'] = 'HOLD'
                dataframe['ai_confidence'] = 0.0
        else:
            # Default values if AI client not available
            dataframe['ai_action'] = 'HOLD'
            dataframe['ai_confidence'] = 0.5
        
        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        # Optional whitelist enforcement for perpetual pairs
        try:
            pair = metadata.get('pair') if isinstance(metadata, dict) else None
            if self.perpetual_whitelist and pair and pair not in self.perpetual_whitelist:
                return dataframe
        except Exception:
            pass

        # Volatility/volume gates
        try:
            enable_vol = bool(self.analysis_cfg.get('enable_volatility_analysis', False))
        except Exception:
            enable_vol = False
        try:
            vol_thr = float(self.analysis_cfg.get('min_micro_volatility_pct', 0.05))
        except Exception:
            vol_thr = 0.05
        try:
            vol_ratio_thr = float(self.analysis_cfg.get('min_volume_ratio', 1.1))
        except Exception:
            vol_ratio_thr = 1.1

        dataframe.loc[
            (dataframe['rsi'] < self.rsi_oversold.value) &
            (dataframe['macd'] > dataframe['macd_signal']) &
            (dataframe['ema_12'] > dataframe['ema_26']) &
            (dataframe['ema_200'] < dataframe['ema_12']) &
            (dataframe['volume_ratio'] > 1.2) &
            (~enable_vol | ((dataframe['micro_vol_std'] >= vol_thr) & (dataframe['volume_ratio'] >= vol_ratio_thr))) &
            (dataframe['ai_action'] == 'BUY') &
            (dataframe['ai_confidence'] > 0.7),
            'enter_long'
        ] = 1
        
        dataframe.loc[
            (dataframe['rsi'] > self.rsi_overbought.value) &
            (dataframe['macd'] < dataframe['macd_signal']) &
            (dataframe['ema_12'] < dataframe['ema_26']) &
            (dataframe['ema_200'] > dataframe['ema_12']) &
            (dataframe['volume_ratio'] > 1.2) &
            (~enable_vol | ((dataframe['micro_vol_std'] >= vol_thr) & (dataframe['volume_ratio'] >= vol_ratio_thr))) &
            (dataframe['ai_action'] == 'SELL') &
            (dataframe['ai_confidence'] > 0.7),
            'enter_short'
        ] = 1
        
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe.loc[
            ((dataframe['rsi'] > self.rsi_overbought.value) |
             (dataframe['macd'] < dataframe['macd_signal'])) &
            (dataframe['volume_ratio'] < 1.5),
            'exit_long'
        ] = 1
        
        dataframe.loc[
            ((dataframe['rsi'] < self.rsi_oversold.value) |
             (dataframe['macd'] > dataframe['macd_signal'])) &
            (dataframe['volume_ratio'] < 1.5),
            'exit_short'
        ] = 1
        
        return dataframe
