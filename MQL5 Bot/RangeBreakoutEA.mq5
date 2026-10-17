#property copyright "MQL5 Strategy Wizard"
// The settings were tuned within MQL5, but this EA was made by Milo
#property link "https://www.mql5.com"
#property version "1.00"
#include <Trade\Trade.mqh>

// Input Parameters
input group "Time Settings"
input int InpRangeStartHour = 3; // Range Start Hour
input int InpRangeStartMinute = 0; // Range Start Minute
input int InpRangeEndHour = 6; // Range End Hour (Breakout Time)
input int InpRangeEndMinute = 0; // Range End Minute
input int InpCloseHour = 20; // Close All Hour
input int InpCloseMinute = 0; // Close All Minute

input group "Risk Management"
input bool InpUsePercentRisk = true; // Use % of Account (true) or Fixed Amount (false)
input double InpRiskPercent = 0.3; // Risk % of Account Balance
input double InpRiskAmount = 50; // Risk Amount per Trade (Money)
input double InpStopLossFactor = 0.75; // Stop Loss Factor (x Range)
input bool InpUseTakeProfit = true; // Use Take Profit
input double InpTakeProfitFactor = 12.5; // Take Profit Factor (x Range)

input group "Strategy Settings"
input bool InpSingleTrade = true; // Single Trade Per Day (OCO)
input bool InpCloseAtTime = true; // Close Positions at Time
input bool InpVisualize = true; // Visualize Range
input ulong InpMagicNumber = 123456;// Magic Number

input group "Month Filter"
input bool InpJanuary = false; // Trade January
input bool InpFebruary = false; // Trade February
input bool InpMarch = true; // Trade March
input bool InpApril = true; // Trade April
input bool InpMay = true; // Trade May
input bool InpJune = false; // Trade June
input bool InpJuly = true; // Trade July
input bool InpAugust = true; // Trade August
input bool InpSeptember = true; // Trade September
input bool InpOctober = true; // Trade October
input bool InpNovember = false; // Trade November
input bool InpDecember = false; // Trade December

input group "Entry Time Filter"
input bool InpUseEntryTimeFilter = false; // Use Entry Time Filter
input int InpEntryStartHour = 12; // Entry Allowed Start Hour
input int InpEntryEndHour = 18; // Entry Allowed End Hour

// Global Variables
CTrade trade;
datetime lastTradeDate = 0;
bool ordersPlaced = false;
double rangeHigh = 0;
double rangeLow = 0;
bool rangeDetermined = false;

int OnInit()
{
   trade.SetExpertMagicNumber(InpMagicNumber);
   return(INIT_SUCCEEDED);
}

void OnTick()
{
   datetime currentTime = TimeCurrent();
   MqlDateTime dt;
   TimeToStruct(currentTime, dt);

   // Month Filter
   if(!IsMonthAllowed(dt.mon)) return;

   // Define time points for today
   datetime dayStart = currentTime - (dt.hour * 3600 + dt.min * 60 + dt.sec);
   datetime rangeStart = dayStart + (InpRangeStartHour * 3600 + InpRangeStartMinute * 60);
   datetime rangeEnd = dayStart + (InpRangeEndHour * 3600 + InpRangeEndMinute * 60);
   datetime closeTime = dayStart + (InpCloseHour * 3600 + InpCloseMinute * 60);

   // 1. New Day Reset
   if(currentTime < rangeStart)
   {
      ordersPlaced = false;
      rangeDetermined = false;
      // Delete only today's objects (preserve historical)
      if(InpVisualize)
      {
         string prefix = "ORB_" + TimeToString(rangeStart);
         ObjectDelete(0, prefix + "_Box");
         ObjectDelete(0, prefix + "_High");
         ObjectDelete(0, prefix + "_Low");
         ObjectDelete(0, prefix + "_HighLabel");
         ObjectDelete(0, prefix + "_LowLabel");
      }
      return;
   }

   // 2. Check Close Time
   if(currentTime >= closeTime)
   {
      if(InpCloseAtTime)
      {
         CloseAllPositions();
      }
      DeletePendingOrders();
      return; // Stop trading for the day
   }

   // 3. During Range
   if(currentTime < rangeEnd)
   {
      // (Wait for range to complete)
   }

   // 4. Range Complete - Place Orders
   if(currentTime >= rangeEnd && !ordersPlaced)
   {
      // Entry Time Filter
      if(InpUseEntryTimeFilter && !IsEntryHourAllowed(dt.hour))
         return;

      // Calculate Range
      if(!CalculateRange(rangeStart, rangeEnd)) return;

      double rangeSize = rangeHigh - rangeLow;
      if(rangeSize <= 0) return;

      if(InpVisualize) DrawRange(rangeStart, rangeEnd, closeTime, rangeHigh, rangeLow);

      // Place Orders or Open Market if breakout occurred
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      
      double slDist = rangeSize * InpStopLossFactor;
      double tpDist = rangeSize * InpTakeProfitFactor;

      // Buy Logic
      if(ask > rangeHigh) // Market Buy Fallback
      {
         double sl = ask - slDist;
         double tp = InpUseTakeProfit ? (ask + tpDist) : 0;
         double vol = CalculateLotSize(MathAbs(ask - sl));
         trade.Buy(vol, _Symbol, ask, sl, tp, "Market Buy Breakout");
      }
      else
      {
         double entry = rangeHigh;
         double sl = entry - slDist;
         double tp = InpUseTakeProfit ? (entry + tpDist) : 0;
         double vol = CalculateLotSize(MathAbs(entry - sl));
         trade.BuyStop(vol, entry, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, closeTime, "Buy Stop Breakout");
      }

      // Sell Logic
      if(bid < rangeLow) // Market Sell Fallback
      {
         double sl = bid + slDist;
         double tp = InpUseTakeProfit ? (bid - tpDist) : 0;
         double vol = CalculateLotSize(MathAbs(sl - bid));
         trade.Sell(vol, _Symbol, bid, sl, tp, "Market Sell Breakout");
      }
      else
      {
         double entry = rangeLow;
         double sl = entry + slDist;
         double tp = InpUseTakeProfit ? (entry - tpDist) : 0;
         double vol = CalculateLotSize(MathAbs(sl - entry));
         trade.SellStop(vol, entry, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, closeTime, "Sell Stop Breakout");
      }

      ordersPlaced = true;
   }

   // 5. OCO Logic (Single Trade Per Day)
   if(InpSingleTrade && ordersPlaced)
   {
      if(PositionsTotal() > 0)
      {
         DeletePendingOrders();
      }
   }
}

bool CalculateRange(datetime start, datetime end)
{
   MqlRates rates[];
   int count = CopyRates(_Symbol, PERIOD_M1, start, end, rates);
   if(count <= 0) return false;

   rangeHigh = rates[0].high;
   rangeLow = rates[0].low;

   for(int i = 1; i < count; i++)
   {
      if(rates[i].high > rangeHigh) rangeHigh = rates[i].high;
      if(rates[i].low < rangeLow) rangeLow = rates[i].low;
   }
   return true;
}

double CalculateLotSize(double slDistancePrice)
{
   if(slDistancePrice <= 0) return 0.01;

   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   if(tickSize == 0 || tickValue == 0) return minLot;

   double riskMoney = InpRiskAmount;
   if(InpUsePercentRisk)
      riskMoney = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPercent / 100.0;

   double volume = riskMoney / ((slDistancePrice / tickSize) * tickValue);

   // Normalize
   volume = MathFloor(volume / lotStep) * lotStep;
   if(volume < minLot) volume = minLot;

   return volume;
}

void DeletePendingOrders()
{
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(OrderGetInteger(ORDER_MAGIC) == InpMagicNumber)
      {
         trade.OrderDelete(ticket);
      }
   }
}

void CloseAllPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {
         trade.PositionClose(ticket);
      }
   }
}

bool IsEntryHourAllowed(int hour)
{
   if(InpEntryStartHour <= InpEntryEndHour)
      return (hour >= InpEntryStartHour && hour < InpEntryEndHour);
   else // Wraps past midnight (e.g. 22 to 6)
      return (hour >= InpEntryStartHour || hour < InpEntryEndHour);
}

bool IsMonthAllowed(int month)
{
   switch(month)
   {
      case 1: return InpJanuary;
      case 2: return InpFebruary;
      case 3: return InpMarch;
      case 4: return InpApril;
      case 5: return InpMay;
      case 6: return InpJune;
      case 7: return InpJuly;
      case 8: return InpAugust;
      case 9: return InpSeptember;
      case 10: return InpOctober;
      case 11: return InpNovember;
      case 12: return InpDecember;
      default: return false;
   }
}

void DrawRange(datetime rangeStart, datetime rangeEnd, datetime closeTime, double high, double low)
{
   string prefix = "ORB_" + TimeToString(rangeStart);

   // Range Box (covers only the range period)
   string boxName = prefix + "_Box";
   if(ObjectFind(0, boxName) < 0)
   {
      ObjectCreate(0, boxName, OBJ_RECTANGLE, 0, rangeStart, high, rangeEnd, low);
      ObjectSetInteger(0, boxName, OBJPROP_COLOR, clrDodgerBlue);
      ObjectSetInteger(0, boxName, OBJPROP_STYLE, STYLE_SOLID);
      ObjectSetInteger(0, boxName, OBJPROP_WIDTH, 2);
      ObjectSetInteger(0, boxName, OBJPROP_FILL, true);
      ObjectSetInteger(0, boxName, OBJPROP_BACK, true);
      ObjectSetInteger(0, boxName, OBJPROP_SELECTABLE, false);
   }

   // Range High Level Line
   string highName = prefix + "_High";
   if(ObjectFind(0, highName) < 0)
   {
      ObjectCreate(0, highName, OBJ_TREND, 0, rangeEnd, high, closeTime, high);
      ObjectSetInteger(0, highName, OBJPROP_COLOR, clrLime);
      ObjectSetInteger(0, highName, OBJPROP_STYLE, STYLE_DASH);
      ObjectSetInteger(0, highName, OBJPROP_WIDTH, 2);
      ObjectSetInteger(0, highName, OBJPROP_RAY_RIGHT, false);
      ObjectSetInteger(0, highName, OBJPROP_BACK, false);
      ObjectSetInteger(0, highName, OBJPROP_SELECTABLE, false);
   }

   // Range Low Level Line
   string lowName = prefix + "_Low";
   if(ObjectFind(0, lowName) < 0)
   {
      ObjectCreate(0, lowName, OBJ_TREND, 0, rangeEnd, low, closeTime, low);
      ObjectSetInteger(0, lowName, OBJPROP_COLOR, clrRed);
      ObjectSetInteger(0, lowName, OBJPROP_STYLE, STYLE_DASH);
      ObjectSetInteger(0, lowName, OBJPROP_WIDTH, 2);
      ObjectSetInteger(0, lowName, OBJPROP_RAY_RIGHT, false);
      ObjectSetInteger(0, lowName, OBJPROP_BACK, false);
      ObjectSetInteger(0, lowName, OBJPROP_SELECTABLE, false);
   }

   // Price Labels
   string highLabel = prefix + "_HighLabel";
   if(ObjectFind(0, highLabel) < 0)
   {
      ObjectCreate(0, highLabel, OBJ_TEXT, 0, rangeEnd, high);
      ObjectSetString(0, highLabel, OBJPROP_TEXT, "  " + DoubleToString(high, _Digits));
      ObjectSetInteger(0, highLabel, OBJPROP_COLOR, clrLime);
      ObjectSetInteger(0, highLabel, OBJPROP_FONTSIZE, 8);
      ObjectSetInteger(0, highLabel, OBJPROP_ANCHOR, ANCHOR_LEFT_LOWER);
      ObjectSetInteger(0, highLabel, OBJPROP_SELECTABLE, false);
   }

   string lowLabel = prefix + "_LowLabel";
   if(ObjectFind(0, lowLabel) < 0)
   {
      ObjectCreate(0, lowLabel, OBJ_TEXT, 0, rangeEnd, low);
      ObjectSetString(0, lowLabel, OBJPROP_TEXT, "  " + DoubleToString(low, _Digits));
      ObjectSetInteger(0, lowLabel, OBJPROP_COLOR, clrRed);
      ObjectSetInteger(0, lowLabel, OBJPROP_FONTSIZE, 8);
      ObjectSetInteger(0, lowLabel, OBJPROP_ANCHOR, ANCHOR_LEFT_UPPER);
      ObjectSetInteger(0, lowLabel, OBJPROP_SELECTABLE, false);
   }

   ChartRedraw(0);
}