// Pine Language - tradingview.com

//@version=3
study(title="TD Sequential", shorttitle="TD Seq", overlay=true)

// This indicator implements a flexible rendition of TD Sequentials
//   Reference: DeMark Indicators by Jason Perl
//
// TD Indicators:
//   - TD Price Flips (TD Setup count = 1)
//   - TD Setup count up (green #, above bar, green diamond if count > 'Setup: Bars') 
//   - TD Setup count down (red #, above bar, red diamond if count > 'Setup: Bars')
//   - TD Sell Setup (red down arrow "setup", above bar)
//   - TD Sell Setup perfected (yellow diamond, above bar), can be deferred
//   - TD Buy Setup (green up arrow "setup", above bar)
//   - TD Buy Setup perfected (yellow diamond, above bar), can be deferred
//   - TD Setup Trend support (green dotted line)
//   - TD Setup Trend resistance (red dotted line)
//   - TD Countdown up (green circle, below bar)
//   - TD Countdown down (red circle, below bar)
//   - TD Sell Countdown qualify bar (blue circle "Q"), 
//   - TD Sell Countdown deferred (green cross, below bar)
//   - TD Sell Countdown (red down arrow "countdown", below bar)
//   - TD Buy Countdown qualify bar (blue circle "Q"), 
//   - TD Buy Countdown deferred (red cross, below bar)
//   - TD Buy Countdown (green up arrow "countdown", below bar)
//   - TD Countdown Recycling (white cross "R", below bar)
//        Note: Only one aspect of recycling is implemented where,  
//           if Setup Up/Down Count == 2 * 'Setup: Bars', then the present Countdown is cancelled.
//           Trend momentum has intensified.
//   - TD Risk Level (blue step line)
//
// Alerts Conditions:
//   "Sell Setup" - Trigger an alert for Sell Setups
//   "Sell Setup Perfected" - Trigger an alert for Perfected Sell Setups
//   "Buy Setup" - Trigger an alert for Buy Setups
//   "Buy Setup Perfected" - Trigger an alert for Perfected Buy Setups
//   "Sell Countdown" - Trigger an alert for Sell Countdowns
//   "Buy Countdown" - Trigger an alert for Buy Countdowns
//   "Countdown Recycle Up" - Trigger an alert for the Countdown Recycle condition, where price is moving up 
//   "Countdown Recycle Down" - Trigger an alert for the Countdown Recycle condition, where price is moving down
//
// "Parameters" and nomenclature:
//   - "Price: Source", defines which bar price to use for price comparisions 
//             (close, hlc3, ohlc4, etc...). Traditionally, close.
//   - TD Setups
//        "Setup: Bars", the last Setup count (traditionally 9). 
//             In this code, called the Buy/Sell Setup event, e.g. the last price up count
//                 becomes the Sell Setup event.
//        "Setup: Lookback bars", defines the previous bar to compare for counting (traditionally 4). 
//        "Setup: Include Equal Price", If enabled, allow >= or <= in price comparisons. 
//             Traditionally not used (default is disabled). Might be useful for intraday charts.
//        "Setup: Perfected Lookback", defines the previous count to evaluate for a perfected setup
//             (this count and the next). Traditionally 3, i.e compare count 6 and 7 to count 8 or count 9.
//             See code below for details.
//        "Setup: Show Count", show/hide setup numbers. 
//             Note: Buy/Sell Setup events are not affected by this setting. They are always shown.
//   - TD Setup Trends (TDST)
//        "Setup Trend: Extend", 
//             If disabled, only look back to the beginning of this Buy/Sell Setup event
//                 to find trends, low(support for Sell) or high(resistance for Buy)
//             If enabled, look back beyond this Buy/Sell Setup event to the previous 
//                 Setup event of the same kind. (This capability has limitations... see code).
//        "Setup Trend: Show", show/hide trend lines
//   - TD Countdowns
//        "Countdown: Bars", the last Countdown count (traditionally 13).
//             Called the Buy/Sell Countdown event in this code, i.e. the last up/down
//                 count becomes the Buy/Sell Countdown event.
//        "Countdown: Lookback Bars", define previous bar to compare for counting (traditionally 2).
//        "Countdown: Qualifier Bar", the bar in the Countdown sequence used to qualifiy the price
//             of the Buy/Sell Countdown event (traditionally 8). If a countdown event doesn't 
//             qualify, it is marked with a "+" symbol and counting continues.
//             Note: If the Qualifier Bar is set >= "Countdown: Lookback Bars", 
//                 qualification is disabled. Countdown events are still determined, just not qualified.
//        "Countdown: Aggressive", Use aggressive comparison. E.g. for Sell Countdown,
//             instead of "Price: Source" >= high of "Countdown: Lookback Bars",
//             use high >= high of "Countdown: Lookback Bars". Disabled by default.
//        "Countdown: Show Count", show/hide countdown numbers. Countdown events are always shown.
//   - TD Risk Level
//        "Risk Level: Show", Show/hide TD Risk Level for setups, countdowns and recycled countdowns.
//
//   If you want more flexibility in the user interface for plotting, set PlotEditEnable = true
//
// Coding notes:
//   - Variable names are hierarchical, to play nicely in a flat namespace.
//        General layout of names: <Indicator><Function><Qualifier><...etc...>
//            Ex) cntdwmCountUp -> <TD Countdown><counting for indicator><counting price moves up>
//   - Variables that start with uppercase represent User input. Otherwise, lowercase. All variables
//        are camelCase.
//   - Plotting parameters are defined at the beginning of each indicator section to
//        faciliate quick/easy alterations. All plots are at the end of the script.
//   - To pull off the logic wizardy of TD Indicators in the Pine Script language, 
//        many series are created. The two basic patters are
//            1) Impulse series (booleans), used to capture events at specific bars
//            2) Stair-step series (integers), used to count impulses across multiple bars


//---- User inputs ---------------------------
PriceSource = input(title="Price: Source", type=source, defval=close)
SetupBars = input(title="Setup: Bars", type=integer, defval=9, minval=4, maxval=31)
SetupLookback = input(title="Setup: Lookback Bars", type=integer, defval=4, minval=1, maxval=14)
SetupEqualEnable = input(title="Setup: Include Equal Price", type=bool, defval=false)
SetupPerfLookback = input(title="Setup: Perfected Lookback", type=integer, defval=3, minval=1, maxval=14)
SetupShowCount = input(title="Setup: Show Count", type=bool, defval=true)
SetupTrendExtend = input(title="Setup Trend: Extend", type=bool, defval=false)
SetupTrendShow = input(title="Setup Trend: Show", type=bool, defval=true)
CntdwnBars = input(title="Countdown: Bars", type=integer, defval=13, minval=3, maxval=31)
CntdwnLookback = input(title="Countdown: Lookback Bars", type=integer, defval=2, minval=1, maxval=30)
CntdwnQualBar = input(title="Countdown: Qualifier Bar", type=integer, defval=8, minval=3, maxval=30)
CntdwnAggressive = input(title="Countdown: Aggressive", type=bool, defval=false)
CntdwnShowCount = input(title="Countdown: Show Count", type=bool, defval=true)
RiskLevelShow = input(title="Risk Level: Show", type=bool, defval=false)
Transp = input(title="Transparency", type=integer, defval=0, minval=0, maxval=100)

PlotEditEnable = false  // show/hide some of the plots from Format window in the user interface.


//---- TD Price Flips ---------------------------
// Plot parameters
// Price Equal plot (pep). Uses plotshape()
pepColor=gray, pepLoc=location.belowbar, pepSize=size.auto, pepStyle=shape.circle

// Create impulse series of price action. Compare where price is greater/less/equal than prior price.
setupPriceUp = (PriceSource > PriceSource[SetupLookback])
setupPriceDown = (PriceSource < PriceSource[SetupLookback])
setupPriceEqual = (PriceSource == PriceSource[SetupLookback])


//---- TD Setups ---------------------------
// Plot parameters
// Setup Count plot (scp)
scpShowLast=144   // Plot char/shapes for previous # of bars, from right edge.
// Setup Count Up plot (scup), Setup Count Down plot (scdp). Uses plotchar()
scupColor=green, scupLoc=location.abovebar, scupSize=size.auto
scdpColor=red,   scdpLoc=location.abovebar, scdpSize=size.auto
// Setup Count Up/Down > Last plot (scuglp/scdglp). Uses plotshape()
scuglpColor=#00900080, scuglpLoc=location.abovebar, scuglpSize=size.auto, scuglpStyle=shape.diamond, scuglpText=""
scdglpColor=#F0000080, scdglpLoc=location.abovebar, scdglpSize=size.auto, scdglpStyle=shape.diamond, scdglpText=""
// Setup Sell plot (ssp), Setup Buy plot (sbp). Uses plotshape()
sspColor=#FF3333, sspLoc=location.abovebar, sspSize=size.normal, sspStyle=shape.arrowdown, sspText="setup"
sbpColor=#33FF33, sbpLoc=location.abovebar, sbpSize=size.normal, sbpStyle=shape.arrowup,   sbpText="setup"
// Setup Sell/Buy Perfected plot (sspp/sbpp). Uses plotshape()
ssppColor=#FFFF0080, ssppLoc=location.abovebar, ssppSize=size.small, ssppStyle=shape.diamond, ssppText=""
sbppColor=#FFFF0080, sbppLoc=location.abovebar, sbppSize=size.small, sbppStyle=shape.diamond, sbppText=""

// Look for the establishment of momentum by counting consecutive up/down price moves.
//   Up/down counters are mutually exclusive; only one is actively counting, while the other is in reset.
// Equal price ticks are captured separately so that up/down ticks aren't active on the
//   same bar. If equal price enabled,
//     Then include equal price in the present up or down count
//     Else ignore equal price and reset count when present
setupCountUp = na
setupCountUp := SetupEqualEnable ?
   (setupPriceUp or (setupCountUp[1] and setupPriceEqual)) ? nz(setupCountUp[1])+1 : 0
   :
   setupPriceUp ? nz(setupCountUp[1])+1 : 0
setupCountDown = na
setupCountDown := SetupEqualEnable ?
   (setupPriceDown or (setupCountDown[1] and setupPriceEqual)) ? nz(setupCountDown[1])+1 : 0
   :
   setupPriceDown ? nz(setupCountDown[1])+1 : 0

// Error check: make sure Setup Up and Down counts don't count on the same bar
// setupCountErrorCheck = setupCountUp and setupCountDown
// plotshape(setupCountErrorCheck, text="Setup Count Error", style=shape.flag, color=yellow, location=location.abovebar, size=size.normal) // debug

// A Setup event is when up/down count == SetupBars
// Sell Setups are defined by up counts, Buy Setups by down counts.
setupSell = na
setupSell := setupCountUp==SetupBars ? valuewhen(setupCountUp==SetupBars, PriceSource, 0) : na
setupBuy = na
setupBuy := setupCountDown==SetupBars ? valuewhen(setupCountDown==SetupBars, PriceSource, 0) : na

// Count bars between setups... used by other indicators
setupSellCount = barssince(setupSell)
setupBuyCount = barssince(setupBuy)

// Perfected Setups
//   For each sell/buy setup, an additional evaluation is performed to determine if it is "perfected".
//   This consists of looking back a few bars and determining if the setup event's price is 
//   higher(sell)/lower(buy) than the lookback bars price. If not, a retest of the lookback
//   bars high/low price is likely.
// SetupPerfLookback (user input) defines which bars to use for perfection evaluation. 
//   Two bars are included in the evaluation: SetupPerfLookback AND SetupPerfLookback+1
// The evalution adheres to DeMark's original definiton where the bar before the setup event
//   also qualifies a perfected setup, even if the setup event bar doesn't qualify.
// Example) Traditional settings: SetupBars=9, SetupPerfLookback=3, 
//   then a sell setup is perfected when 
//       ( (high(8) >= high(6)) and (high(8) >= high(7)) ) or   // start evaluation
//       ( (high(9) >= high(6)) and (high(9) >= high(7)) ) or 
//       ...
//       ( (high(9+n) >= high(6)) and (high(9+n) >= high(7)) )  // continued eval
//   where n counts past the setup event, on setupCountUp bars. The evalution
//   continues until the logic evaluates true, or cancelled.
// Cancelation rules for perfection evaluation aren't clear...(?) So here's a liberal approach:
//   - If a Setup event in the same direction appears, re-start
//   - If a Setup event in the opposite direction appears, cancel

// To evaluate perfected setups, create additional series: 
//   - A perfect price series, used for comparision to the setup event price or beyond
//   - A mask series which holds the decision logic of "perfected" or "deffered"
//     After the mask is created, it overlays setup count series to plot visual indicators.
// For convenience, define const integer variables to translate the meaning of perfected/deffered
setupIsPerfected = 2 
setupIsDeferred = 1 

// Perfected Sell Setup events
// Get the price for which Sell Setup perfection is evaluated. Stair-step series.
setupSellPerfPrice = na
setupSellPerfPrice := setupCountUp==SetupBars ?
   ((valuewhen(setupCountUp==(SetupBars-SetupPerfLookback), high, 0) >= 
      valuewhen(setupCountUp==(SetupBars-SetupPerfLookback+1), high, 0)) ? 
         valuewhen(setupCountUp==(SetupBars-SetupPerfLookback), high, 0 ) :
         valuewhen(setupCountUp==(SetupBars-SetupPerfLookback+1), high, 0 )
   ) : nz(setupSellPerfPrice[1])
//plot(setupSellPerfPrice, color=yellow, linewidth=2)  // debug

// Create mask to hold "perfected" decisions. This is like a state-machine, where new inputs
//   determine what to do next. The logic:
// First, cancellation
//   - If a perfected event found, cancel (done)
//   - If a Buy Setup event occurs, cancel. This Sell Setup trend is over.
// Second, start (or re-start) evaluation
//   - If a new Setup Sell event is present, start. Compare SetupBars and (SetupBars-1) to perf price.
//       If one of these bars passes, then set mask to perfected. 
//       Else, set mask to deferred and continue evaluaton.
// Third, continue evaluation
//   - If mask is deffered, check any bar (count up or down) for perfection, until cancelation. 
//   - If a perfected Sell Setup event NOT found, then seamlessly roll into the next Sell Setup event.
setupSellPerfMask = na
setupSellPerfMask := 
   ((nz(setupSellPerfMask[1])>=setupIsPerfected) or (not na(setupBuy))) ? na : 
      setupCountUp==SetupBars ? 
         ((valuewhen(setupCountUp==(SetupBars-1), high, 0) >= setupSellPerfPrice) or 
          (valuewhen(setupCountUp==SetupBars, high, 0) >= setupSellPerfPrice)) ?
             setupIsPerfected : setupIsDeferred 
         : 
         na(setupSellPerfMask[1]) ? na : 
           high>=setupSellPerfPrice ? setupIsPerfected : setupSellPerfMask[1]

// Get the perfected bar for plotting later
setupSellPerf = setupSellPerfMask==setupIsPerfected ? PriceSource : na

// Perfected Buy Setup events
setupBuyPerfPrice = na
setupBuyPerfPrice := setupCountDown==SetupBars ?
   ((valuewhen(setupCountDown==(SetupBars-SetupPerfLookback), low, 0) <= 
      valuewhen(setupCountDown==(SetupBars-SetupPerfLookback+1), low, 0)) ? 
         valuewhen(setupCountDown==(SetupBars-SetupPerfLookback), low, 0 ) :
         valuewhen(setupCountDown==(SetupBars-SetupPerfLookback+1), low, 0 )
   ) : nz(setupBuyPerfPrice[1])
//plot(setupBuyPerfPrice, color=yellow, linewidth=2)  // debug

setupBuyPerfMask = na
setupBuyPerfMask := 
   ((nz(setupBuyPerfMask[1])>=setupIsPerfected) or (not na(setupSell))) ? na : 
      setupCountDown==SetupBars ? 
         ((valuewhen(setupCountDown==(SetupBars-1), low, 0) <= setupBuyPerfPrice) or 
          (valuewhen(setupCountDown==SetupBars, low, 0) <= setupBuyPerfPrice)) ?
             setupIsPerfected : setupIsDeferred 
         : 
         na(setupBuyPerfMask[1]) ? na : 
           low<=setupBuyPerfPrice ? setupIsPerfected : setupBuyPerfMask[1]

setupBuyPerf = setupBuyPerfMask==setupIsPerfected ? PriceSource : na


//---- TD Setup Trend (TDST) ---------------------------
// Plot parameters
// Setup Trend Support/Resistance plot (stsp/strp). Uses plot()
stspColor=#99FF99, stspStyle=circles, stspOffset=0 //=(1-SetupBars)
strpColor=#FF9999, strpStyle=circles, strpOffset=0 //=(1-SetupBars)
// Shading between support/resistance lines. Uses fill()
stpColorNormal=#00000000   // Support is below resistance (#00000000 = no color and transparent)
stpColorFlip  =#20202040   // Support is above resistance, flipped

// TDSTs are support/resistance lines, i.e. the lowest/highest price since: 
//   1) The beginning of this Setup (price flip, count==1), or
//   2) The previous Setup of the same trend, e.g. if a Sell Setup, then low(support) from previous Sell Setup
//      This option is enabled by user input "Setup Trend: Extend"
// Support is established at the beginning of (or prior to) a up/sell trend.
// Resistance is established at the beginning of (or prior to) a down/buy trend.

// Limitations of Extended Setup Trend:
//   Cludgy coding... unable to properly extract setupSellCount from seris and hand it to
//     the lowest() function as integer.
//   if/else logic only allows for steps of "SetupBars" to look for lowest/highest,
//     thus resolution is "chuncky". 
//   Stop at 10*SetupBars to avoid script consuming too much server juice... and rejected.
// TODO: Is there a better way to code extended trend lines?
setupTrendSupport = na
setupTrendSupport := setupSell ? 
   (SetupTrendExtend ? (
      setupSellCount[1] <=   SetupBars ? lowest(SetupBars) : 
      setupSellCount[1] <= 2*SetupBars ? lowest(2*SetupBars) :
      setupSellCount[1] <= 3*SetupBars ? lowest(3*SetupBars) :
      setupSellCount[1] <= 4*SetupBars ? lowest(4*SetupBars) :
      setupSellCount[1] <= 5*SetupBars ? lowest(5*SetupBars) :
      setupSellCount[1] <= 6*SetupBars ? lowest(6*SetupBars) :
      setupSellCount[1] <= 7*SetupBars ? lowest(7*SetupBars) :
      setupSellCount[1] <= 8*SetupBars ? lowest(8*SetupBars) :
      setupSellCount[1] <= 9*SetupBars ? lowest(9*SetupBars) : lowest(10*SetupBars))
      : lowest(SetupBars) )
   : nz(setupTrendSupport[1])
setupTrendResist = na
setupTrendResist := setupBuy ? 
   (SetupTrendExtend ? (
      setupBuyCount[1] <=   SetupBars ? highest(SetupBars) : 
      setupBuyCount[1] <= 2*SetupBars ? highest(2*SetupBars) : 
      setupBuyCount[1] <= 3*SetupBars ? highest(3*SetupBars) : 
      setupBuyCount[1] <= 4*SetupBars ? highest(4*SetupBars) : 
      setupBuyCount[1] <= 5*SetupBars ? highest(5*SetupBars) : 
      setupBuyCount[1] <= 6*SetupBars ? highest(6*SetupBars) : 
      setupBuyCount[1] <= 7*SetupBars ? highest(7*SetupBars) : 
      setupBuyCount[1] <= 8*SetupBars ? highest(8*SetupBars) : 
      setupBuyCount[1] <= 9*SetupBars ? highest(9*SetupBars) : highest(10*SetupBars))
      : highest(SetupBars))
   : nz(setupTrendResist[1])


//---- TD Countdown ---------------------------
// Plot parameters
// Countdown Count Up/Down plot (ccup/ccdp). Uses plotshape()
ccupColor=green, ccupLoc=location.belowbar, ccupSize=size.auto, ccupStyle=shape.circle  // no text
ccdpColor=red,   ccdpLoc=location.belowbar, ccdpSize=size.auto, ccdpStyle=shape.circle  // no text
// Countdown Last Count Up/Down plot (clcup/clcdp). Uses plotshape()
clcupColor=#33FF33, clcupLoc=location.belowbar, clcupSize=size.auto, clcupStyle=shape.circle  // no text
clcdpColor=#FF8333, clcdpLoc=location.belowbar, clcdpSize=size.auto, clcdpStyle=shape.circle  // no text
// Countdown Qualification Count plot (cqcp). Uses plotshape() ...only one defintion for both up/down counts
cqcpColor=#4444FF, cqcpLoc=location.belowbar, cqcpSize=size.auto, cqcpStyle=shape.diamond, cqcpText="Q"
// Countdown Count Recycle plot (cqcp). Uses plotshape() ...only one defintion for both up/down counts
ccrpColor=white, ccrpLoc=location.belowbar, ccrpSize=size.auto, ccrpStyle=shape.cross, ccrpText="R"
// Countdown Sell/Buy Deferred plot (csdp/cbdp). Uses plotshape()
csdpColor=green, csdpLoc=location.belowbar, csdpSize=size.auto, csdpStyle=shape.cross, csdpText=""
cbdpColor=red,   cbdpLoc=location.belowbar, cbdpSize=size.auto, cbdpStyle=shape.cross, cbdpText=""
// Countdown Sell/Buy event plot (csp/cbp). Uses plotshape()
cspColor=#FF3333, cspLoc=location.belowbar, cspSize=size.normal, cspStyle=shape.arrowdown, cspText="count\ndown"
cbpColor=#33FF33, cbpLoc=location.belowbar, cbpSize=size.normal, cbpStyle=shape.arrowup,   cbpText="count\ndown"
// Countdown Sell/Buy Aggressive event plot (csap/cbap)... same as csp/cbp, except text
csapText="aggr\ncount\ndown"
cbapText="aggr\ncount\ndown"

// Compare where price is greater/less than prior price
cntdwnPriceUp = CntdwnAggressive ? (high >= high[CntdwnLookback]) : (PriceSource >= high[CntdwnLookback])
cntdwnPriceDown = CntdwnAggressive ? (low <= low[CntdwnLookback]) : (PriceSource <= low[CntdwnLookback])

//plotshape(cntdwnPriceUp?true:na, style=shape.circle, color=gray, location=location.belowbar, size=size.auto, transp=Transp)  // debug
//plotshape(cntdwnPriceDown?true:na, style=shape.circle, color=white, location=location.belowbar, size=size.auto, transp=Transp)  // debug

// Determine Setup recycle events
cntdwnCountUpRecycle = na
cntdwnCountUpRecycle := (setupCountUp==(2*SetupBars)) ? valuewhen((setupCountUp==(2*SetupBars)), PriceSource, 0) : na
cntdwnCountDownRecycle = na
cntdwnCountDownRecycle := (setupCountDown==(2*SetupBars)) ? valuewhen((setupCountDown==(2*SetupBars)), PriceSource, 0) : na

// Count up/down price moves. Price moves don't have to be consecutive for TD Countdowns
// "na" means no counting, integer values (including zero) mean a count in progress
// If countdown cancellation rules appear, stop counting. Else,
//   If a sell setup appears, start counting on this setup bar. Else,
//     If previous value is counting, continue counting on this bar. Else... do nothing
cntdwnCountUp = na
// Note: One of the cancellation rules { stop counting at CntdwnBars, i.e. (nz(cntdwnCountUp[1])>=CntdwnBars) }
//   is removed from this construct. This facilitates "qualification" in the next step.
cntdwnCountUp := na(cntdwnPriceUp) ? cntdwnCountUp[1] :
   ((not na(setupBuy)) or (PriceSource<setupTrendSupport) or (not na(cntdwnCountUpRecycle))) ? na :
      ((not na(setupSell)) ? (cntdwnPriceUp ? 1 : 0) :
         na(cntdwnCountUp[1]) ? na : (cntdwnPriceUp ? cntdwnCountUp[1]+1 : cntdwnCountUp[1])
      )
// Convert stair-step values to impulse, i.e. only keep the initial price move
cntdwnCountUpImp = na
cntdwnCountUpImp := cntdwnPriceUp ? cntdwnCountUp : na

cntdwnCountDown = na
cntdwnCountDown := na(cntdwnPriceDown) ? cntdwnCountDown[1] :
   ((not na(setupSell)) or (PriceSource>setupTrendResist) or (not na(cntdwnCountDownRecycle))) ? na :
      ((not na(setupBuy)) ? (cntdwnPriceDown ? 1 : 0) :
         na(cntdwnCountDown[1]) ? na : (cntdwnPriceDown ? cntdwnCountDown[1]+1 : cntdwnCountDown[1])
      )
// plot(cntdwnCountDown, color=yellow, linewidth=2)  // debug
cntdwnCountDownImp = na
cntdwnCountDownImp := cntdwnPriceDown ? cntdwnCountDown : na

// Qualification of Countdowns: The last Countdown price must be greater/less than the CntdwnQualBar price
cntdwnIsQualified = 2  // value in qual mask series when countdown event is qualified
cntdwnIsDeferred = 1 

cntdwnSellQualPrice = na
cntdwnSellQualMask = na
cntdwnSellQualMaskImp = na
cntdwnBuyQualPrice = na
cntdwnBuyQualMask = na
cntdwnBuyQualMaskImp = na

if (CntdwnQualBar < CntdwnBars)
    // Get the price at CntdwnQualBar, create stair-step function of value
    cntdwnSellQualPrice := cntdwnCountUpImp==CntdwnQualBar ? 
       valuewhen(cntdwnCountUpImp==CntdwnQualBar, PriceSource, 0) : nz(cntdwnSellQualPrice[1])
    // Create mask series, a stair-step function that qualifies:
    //   If "count up price" > "qualify price", then set mask=cntdwnIsQualified. 
    //     This is THE Sell Countdown event, qualified.
    //   If "count up price" <= "qualify price", then set mask=cntdwnIsDeferred. 
    //     Still looked for qualified Sell Countdown event.
    // Same routine as cntdwnCountUp... "na" means not qualifying. Integers mean qualifying in progress.
    //   If previous mask value is cntdwnIsQualified or count up is cancelled, stop qualifying. Else,
    //     If at CntdwnBars, start qualifying. Else,
    //       If previous mask is cntdwnIsDeferred, continue qualifying. Else, do nothing
    cntdwnSellQualMask := 
       (nz(cntdwnSellQualMask[1])>=cntdwnIsQualified) or na(cntdwnCountUp) ? na :
          (cntdwnCountUpImp==CntdwnBars ?
             (valuewhen(cntdwnCountUpImp==CntdwnBars, high, 0) >= cntdwnSellQualPrice ? 
               cntdwnIsQualified : cntdwnIsDeferred) : 
             (na(cntdwnSellQualMask[1]) ? na :
               (cntdwnCountUpImp>CntdwnBars ?
                  (valuewhen(cntdwnCountUpImp>CntdwnBars, high, 0) >= cntdwnSellQualPrice ? 
                     cntdwnIsQualified : cntdwnSellQualMask[1]) :
                  cntdwnSellQualMask[1])))

    cntdwnBuyQualPrice := cntdwnCountDownImp==CntdwnQualBar ? 
      valuewhen(cntdwnCountDownImp==CntdwnQualBar, PriceSource, 0) : nz(cntdwnBuyQualPrice[1])
    cntdwnBuyQualMask := 
       (nz(cntdwnBuyQualMask[1])>=cntdwnIsQualified) or na(cntdwnCountDown) ? na :
          (cntdwnCountDownImp==CntdwnBars ?
             (valuewhen(cntdwnCountDownImp==CntdwnBars, low, 0) <= cntdwnBuyQualPrice ? 
               cntdwnIsQualified : cntdwnIsDeferred) : 
             (na(cntdwnBuyQualMask[1]) ? na :
               (cntdwnCountDownImp>CntdwnBars ?
                  (valuewhen(cntdwnCountDownImp>CntdwnBars, low, 0) <= cntdwnBuyQualPrice ? 
                     cntdwnIsQualified : cntdwnBuyQualMask[1]) :
                  cntdwnBuyQualMask[1])))
else
    cntdwnSellQualMask := cntdwnCountUp==CntdwnBars ? cntdwnIsQualified : na
    cntdwnBuyQualMask := cntdwnCountDown==CntdwnBars ? cntdwnIsQualified : na

// Get the impulse version of the stair-step qualification mask
cntdwnSellQualMaskImp := cntdwnCountUpImp ? cntdwnSellQualMask : na
cntdwnBuyQualMaskImp := cntdwnCountDownImp ? cntdwnBuyQualMask : na

// plot(cntdwnSellQualPrice, style=line, linewidth=2, color=orange)  // debug
// plot(cntdwnBuyQualPrice, style=line, linewidth=2, color=white)  // debug

// A Sell/Buy Countdown event is when up/down count == CountdownBars
//   Sell Countdowns are defined by up counts, Buy Countdowns by down counts...
cntdwnSell = na
cntdwnSellDefer = na
cntdwnSell := cntdwnSellQualMaskImp==cntdwnIsQualified ? 
   valuewhen(cntdwnSellQualMaskImp==cntdwnIsQualified, PriceSource, 0) : na
cntdwnSellDefer := cntdwnSellQualMaskImp==cntdwnIsDeferred ? 
   valuewhen(cntdwnSellQualMaskImp==cntdwnIsDeferred, PriceSource, 0) : na

cntdwnBuy = na
cntdwnBuyDefer = na
cntdwnBuy := cntdwnBuyQualMaskImp==cntdwnIsQualified ? 
   valuewhen(cntdwnBuyQualMaskImp==cntdwnIsQualified, PriceSource, 0) : na
cntdwnBuyDefer := cntdwnBuyQualMaskImp==cntdwnIsDeferred ? 
   valuewhen(cntdwnBuyQualMaskImp==cntdwnIsDeferred, PriceSource, 0) : na

// TD Risk Levels for setup and countdown
riskLevel = na, riskBar = na
//riskBar :=
//   setupSell ? highest(SetupBars)
riskLevel :=
   setupSell or cntdwnCountUpRecycle ? (highest(SetupBars)+valuewhen(high==highest(SetupBars), tr, 0)) :
   setupBuy or cntdwnCountDownRecycle ? (lowest(SetupBars)-valuewhen(low==lowest(SetupBars), tr, 0)) :
   cntdwnSell ? (highest(CntdwnBars)+valuewhen(high==highest(CntdwnBars), tr, 0)) :
   cntdwnBuy ? (lowest(CntdwnBars)-valuewhen(low==lowest(CntdwnBars), tr, 0)) : nz(riskLevel[1], low)

//---- Alert conditions ---------------------------
alertcondition(setupSell, title="Sell Setup", message="Sell Setup")
alertcondition(setupSellPerf, title="Sell Setup Perfected", message="Sell Setup Perfected")
alertcondition(setupBuy, title="Buy Setup", message="Buy Setup")
alertcondition(setupBuyPerf, title="Buy Setup Perfected", message="Buy Setup Perfected")
alertcondition(cntdwnSell, title="Sell Countdown", message="Sell Countdown")
alertcondition(cntdwnBuy, title="Buy Countdown", message="Buy Countdown")
alertcondition(cntdwnCountUpRecycle, title="Countdown Recycle Up", message="Countdown Recycle Up")
alertcondition(cntdwnCountDownRecycle, title="Countdown Recycle Down", message="Countdown Recycle Down")

//---- Plot everything ---------------------------
// Background plots come first. Shapes that need to be on top are last.

// TDST (Support/Resistance)
//   Use plot offset to move line back to beginning of Setup count...
stsp=plot(SetupTrendShow?setupTrendSupport:na, title="TDST Support",    style=stspStyle, color=stspColor, linewidth=2, offset=stspOffset)
strp=plot(SetupTrendShow?setupTrendResist:na,  title="TDST Resistance", style=strpStyle, color=strpColor, linewidth=2, offset=strpOffset)
// Shade area between support/resistance lines
fill(stsp, strp, title="TDST plot fill", color=(setupTrendSupport>setupTrendResist)?stpColorFlip:stpColorNormal)

// TD Risk Levels
plot(RiskLevelShow?riskLevel:na, title="TD Risk Level", style=stepline, color=teal, linewidth=2)

// Experimental plot... High visibility vertical lines on setup events
// setupEventColor = setupSell ? #FF2222A0 : (setupBuy ? #00FF0060 : #00000000)
// bgcolor(setupEventColor)

// Show where equal price bars occur, if enabled
plotshape(SetupEqualEnable?(setupPriceEqual?true:na):na, title="Equal Price Compare", style=pepStyle, color=pepColor, location=pepLoc, size=pepSize, transp=Transp)

// Plot Countdown with numbers
// plotshape(CntdwnShowCount?(cntdwnCountUpImp<8?true:na):na,     title="Countdowns Up <8",             style=ccupStyle, color=ccupColor, location=ccupLoc, size=ccupSize, transp=Transp, editable=PlotEditEnable)
// plotshape(CntdwnShowCount?(cntdwnCountUpImp==8?true:na):na,    title="Countdown Up 8",    text="8",  style=ccupStyle, color=ccupColor, location=ccupLoc, size=ccupSize, transp=Transp, editable=PlotEditEnable)
// plotshape(CntdwnShowCount?(cntdwnCountUpImp==9?true:na):na,    title="Countdown Up 9",    text="9",  style=ccupStyle, color=ccupColor, location=ccupLoc, size=ccupSize, transp=Transp, editable=PlotEditEnable)
// plotshape(CntdwnShowCount?(cntdwnCountUpImp==10?true:na):na,   title="Countdown Up 10",   text="10", style=ccupStyle, color=ccupColor, location=ccupLoc, size=ccupSize, transp=Transp, editable=PlotEditEnable)
// plotshape(CntdwnShowCount?(cntdwnCountUpImp==11?true:na):na,   title="Countdown Up 11",   text="11", style=ccupStyle, color=ccupColor, location=ccupLoc, size=ccupSize, transp=Transp, editable=PlotEditEnable)
// plotshape(CntdwnShowCount?(cntdwnCountUpImp==12?true:na):na,   title="Countdown Up 12",   text="12", style=ccupStyle, color=ccupColor, location=ccupLoc, size=ccupSize, transp=Transp, editable=PlotEditEnable)

// plotshape(CntdwnShowCount?(cntdwnCountDownImp<8?true:na):na,   title="Countdowns Down <8",           style=ccdpStyle, color=ccdpColor, location=ccdpLoc, size=ccdpSize, transp=Transp, editable=PlotEditEnable)
// plotshape(CntdwnShowCount?(cntdwnCountDownImp==8?true:na):na,  title="Countdown Down 8",  text="8",  style=ccdpStyle, color=ccdpColor, location=ccdpLoc, size=ccdpSize, transp=Transp, editable=PlotEditEnable)
// plotshape(CntdwnShowCount?(cntdwnCountDownImp==9?true:na):na,  title="Countdown Down 9",  text="9",  style=ccdpStyle, color=ccdpColor, location=ccdpLoc, size=ccdpSize, transp=Transp, editable=PlotEditEnable)
// plotshape(CntdwnShowCount?(cntdwnCountDownImp==10?true:na):na, title="Countdown Down 10", text="10", style=ccdpStyle, color=ccdpColor, location=ccdpLoc, size=ccdpSize, transp=Transp, editable=PlotEditEnable)
// plotshape(CntdwnShowCount?(cntdwnCountDownImp==11?true:na):na, title="Countdown Down 11", text="11", style=ccdpStyle, color=ccdpColor, location=ccdpLoc, size=ccdpSize, transp=Transp, editable=PlotEditEnable)
// plotshape(CntdwnShowCount?(cntdwnCountDownImp==12?true:na):na, title="Countdown Down 12", text="12", style=ccdpStyle, color=ccdpColor, location=ccdpLoc, size=ccdpSize, transp=Transp, editable=PlotEditEnable)

// Plot Countdown with shapes only
plotshape(CntdwnShowCount?(cntdwnCountUpImp<CntdwnBars?true:na):na,
   title="Countdowns Up < Last", style=ccupStyle, color=ccupColor, location=ccupLoc, size=ccupSize, transp=Transp, editable=PlotEditEnable)
plotshape(CntdwnShowCount?(cntdwnCountUpImp==CntdwnBars?true:na):na,
   title="Countdowns Last Up", style=clcupStyle, color=clcupColor, location=clcupLoc, size=clcupSize, transp=Transp, editable=PlotEditEnable)
plotshape(CntdwnShowCount?(cntdwnCountDownImp<CntdwnBars?true:na):na,   
   title="Countdowns Down < Last", style=ccdpStyle, color=ccdpColor, location=ccdpLoc, size=ccdpSize, transp=Transp, editable=PlotEditEnable)
plotshape(CntdwnShowCount?(cntdwnCountDownImp==CntdwnBars?true:na):na,   
   title="Countdowns Last Down", style=clcdpStyle, color=clcdpColor, location=clcdpLoc, size=clcdpSize, transp=Transp, editable=PlotEditEnable)

// Plot Countdown qualify bar
plotshape(CntdwnShowCount?((cntdwnCountUpImp==CntdwnQualBar)or(cntdwnCountDownImp==CntdwnQualBar)?true:na):na, 
   title="Countdown Qual Bar", text=cqcpText, style=cqcpStyle, color=cqcpColor, location=cqcpLoc, size=cqcpSize, transp=Transp, editable=PlotEditEnable)
// Plot Countdown recycle
plotshape(CntdwnShowCount?(cntdwnCountUpRecycle or cntdwnCountDownRecycle):na, 
   title="Countdown Recycle", text=ccrpText, style=ccrpStyle, color=ccrpColor, location=ccrpLoc, size=ccrpSize, transp=Transp, editable=PlotEditEnable)

// Plot setup buy/sell events
// Note: this code is placed here so that setup shapes are placed on top of countdown shapes
plotshape(setupSell, title="Sell Setup", text=sspText, style=sspStyle, color=sspColor, location=sspLoc, size=sspSize, transp=Transp)
plotshape(setupBuy,  title="Buy Setup",  text=sbpText, style=sbpStyle, color=sbpColor, location=sbpLoc, size=sbpSize, transp=Transp)
// Plot setup buy/sell perfected indicator
plotshape(setupSellPerf, title="Perfected Sell Setup", text=ssppText, style=ssppStyle, color=ssppColor, location=ssppLoc, size=ssppSize, transp=Transp)
plotshape(setupBuyPerf,  title="Perfected Buy Setup",  text=sbppText, style=sbppStyle, color=sbppColor, location=sbppLoc, size=sbppSize, transp=Transp)


// Plot Countdown Sell/Buy Deferred event
plotshape(cntdwnSellDefer, title="Sell Countdown Deferred", text=csdpText, style=csdpStyle, color=csdpColor, location=csdpLoc, size=csdpSize, transp=Transp)
plotshape(cntdwnBuyDefer,  title="Buy Countdown Deferred",  text=cbdpText, style=cbdpStyle, color=cbdpColor, location=cbdpLoc, size=cbdpSize, transp=Transp)
// Plot Countdown Sell/Buy event
plotshape(CntdwnAggressive?na:cntdwnSell, title="Sell Countdown", text=cspText, style=cspStyle, color=cspColor, location=cspLoc, size=cspSize, transp=Transp)
plotshape(CntdwnAggressive?na:cntdwnBuy,  title="Buy Countdown",  text=cbpText, style=cbpStyle, color=cbpColor, location=cbpLoc, size=cbpSize, transp=Transp)
plotshape(CntdwnAggressive?cntdwnSell:na, title="Aggressive Sell Countdown", text=csapText, style=cspStyle, color=cspColor, location=cspLoc, size=cspSize, transp=Transp)
plotshape(CntdwnAggressive?cntdwnBuy:na,  title="Aggressive Buy Countdown",  text=cbapText, style=cbpStyle, color=cbpColor, location=cbpLoc, size=cbpSize, transp=Transp)

// Setups, last
// Plot Setup up/down counts
plotchar(SetupShowCount?((setupCountUp==1)?true:na):na,                    title="Setup Count Up 1",  char="1", color=scupColor, location=scupLoc, size=scupSize, transp=Transp, editable=PlotEditEnable)
plotchar(SetupShowCount?((setupCountUp==2)and(2<=SetupBars)?true:na):na,   title="Setup Count Up 2",  char="2", color=scupColor, location=scupLoc, size=scupSize, transp=Transp, editable=PlotEditEnable, show_last=scpShowLast)
plotchar(SetupShowCount?((setupCountUp==3)and(3<=SetupBars)?true:na):na,   title="Setup Count Up 3",  char="3", color=scupColor, location=scupLoc, size=scupSize, transp=Transp, editable=PlotEditEnable, show_last=scpShowLast)
plotchar(SetupShowCount?((setupCountUp==4)and(4<=SetupBars)?true:na):na,   title="Setup Count Up 4",  char="4", color=scupColor, location=scupLoc, size=scupSize, transp=Transp, editable=PlotEditEnable, show_last=scpShowLast)
plotchar(SetupShowCount?((setupCountUp==5)and(5<=SetupBars)?true:na):na,   title="Setup Count Up 5",  char="5", color=scupColor, location=scupLoc, size=scupSize, transp=Transp, editable=PlotEditEnable)
plotchar(SetupShowCount?((setupCountUp==6)and(6<=SetupBars)?true:na):na,   title="Setup Count Up 6",  char="6", color=scupColor, location=scupLoc, size=scupSize, transp=Transp, editable=PlotEditEnable, show_last=scpShowLast)
plotchar(SetupShowCount?((setupCountUp==7)and(7<=SetupBars)?true:na):na,   title="Setup Count Up 7",  char="7", color=scupColor, location=scupLoc, size=scupSize, transp=Transp, editable=PlotEditEnable)
plotchar(SetupShowCount?((setupCountUp==8)and(8<=SetupBars)?true:na):na,   title="Setup Count Up 8",  char="8", color=scupColor, location=scupLoc, size=scupSize, transp=Transp, editable=PlotEditEnable, show_last=scpShowLast)
plotchar(SetupShowCount?((setupCountUp==9)and(9<=SetupBars)?true:na):na,   title="Setup Count Up 9",  char="9", color=scupColor, location=scupLoc, size=scupSize, transp=Transp, editable=PlotEditEnable)
// For values > 9, use hexadecimal values since we can only plot one char
plotchar(SetupShowCount?((setupCountUp==10)and(10<=SetupBars)?true:na):na, title="Setup Count Up 10", char="A", color=scupColor, location=scupLoc, size=scupSize, transp=Transp, editable=PlotEditEnable)
plotchar(SetupShowCount?((setupCountUp==11)and(11<=SetupBars)?true:na):na, title="Setup Count Up 11", char="B", color=scupColor, location=scupLoc, size=scupSize, transp=Transp, editable=PlotEditEnable)
plotchar(SetupShowCount?((setupCountUp==12)and(12<=SetupBars)?true:na):na, title="Setup Count Up 12", char="C", color=scupColor, location=scupLoc, size=scupSize, transp=Transp, editable=PlotEditEnable)
plotchar(SetupShowCount?((setupCountUp==13)and(13<=SetupBars)?true:na):na, title="Setup Count Up 13", char="D", color=scupColor, location=scupLoc, size=scupSize, transp=Transp, editable=PlotEditEnable)
// plotchar(SetupShowCount?((setupCountUp==14)and(14<=SetupBars)?true:na):na, title="Setup Count Up 14", char="E", color=scupColor, location=scupLoc, size=scupSize, transp=Transp, editable=PlotEditEnable)
// plotchar(SetupShowCount?((setupCountUp==15)and(15<=SetupBars)?true:na):na, title="Setup Count Up 15", char="F", color=scupColor, location=scupLoc, size=scupSize, transp=Transp, editable=PlotEditEnable)
plotshape(SetupShowCount?((setupCountUp>SetupBars)?true:na):na, title="Setup Count Up > Last",  
   text=scuglpText, style=scuglpStyle, color=scuglpColor, location=scuglpLoc, size=scuglpSize, transp=Transp, editable=PlotEditEnable)

plotchar(SetupShowCount?((setupCountDown==1)?true:na):na,                    title="Setup Count Down 1",  char="1", color=scdpColor, location=scdpLoc, size=scdpSize, transp=Transp, editable=PlotEditEnable)
plotchar(SetupShowCount?((setupCountDown==2)and(2<=SetupBars)?true:na):na,   title="Setup Count Down 2",  char="2", color=scdpColor, location=scdpLoc, size=scdpSize, transp=Transp, editable=PlotEditEnable, show_last=scpShowLast)
plotchar(SetupShowCount?((setupCountDown==3)and(3<=SetupBars)?true:na):na,   title="Setup Count Down 3",  char="3", color=scdpColor, location=scdpLoc, size=scdpSize, transp=Transp, editable=PlotEditEnable, show_last=scpShowLast)
plotchar(SetupShowCount?((setupCountDown==4)and(4<=SetupBars)?true:na):na,   title="Setup Count Down 4",  char="4", color=scdpColor, location=scdpLoc, size=scdpSize, transp=Transp, editable=PlotEditEnable, show_last=scpShowLast)
plotchar(SetupShowCount?((setupCountDown==5)and(5<=SetupBars)?true:na):na,   title="Setup Count Down 5",  char="5", color=scdpColor, location=scdpLoc, size=scdpSize, transp=Transp, editable=PlotEditEnable)
plotchar(SetupShowCount?((setupCountDown==6)and(6<=SetupBars)?true:na):na,   title="Setup Count Down 6",  char="6", color=scdpColor, location=scdpLoc, size=scdpSize, transp=Transp, editable=PlotEditEnable, show_last=scpShowLast)
plotchar(SetupShowCount?((setupCountDown==7)and(7<=SetupBars)?true:na):na,   title="Setup Count Down 7",  char="7", color=scdpColor, location=scdpLoc, size=scdpSize, transp=Transp, editable=PlotEditEnable)
plotchar(SetupShowCount?((setupCountDown==8)and(8<=SetupBars)?true:na):na,   title="Setup Count Down 8",  char="8", color=scdpColor, location=scdpLoc, size=scdpSize, transp=Transp, editable=PlotEditEnable, show_last=scpShowLast)
plotchar(SetupShowCount?((setupCountDown==9)and(9<=SetupBars)?true:na):na,   title="Setup Count Down 9",  char="9", color=scdpColor, location=scdpLoc, size=scdpSize, transp=Transp, editable=PlotEditEnable)
// For values > 9, use hexadecimal values since we can only plot one char
plotchar(SetupShowCount?((setupCountDown==10)and(10<=SetupBars)?true:na):na, title="Setup Count Down 10", char="A", color=scdpColor, location=scdpLoc, size=scdpSize, transp=Transp, editable=PlotEditEnable)
plotchar(SetupShowCount?((setupCountDown==11)and(11<=SetupBars)?true:na):na, title="Setup Count Down 11", char="B", color=scdpColor, location=scdpLoc, size=scdpSize, transp=Transp, editable=PlotEditEnable)
plotchar(SetupShowCount?((setupCountDown==12)and(12<=SetupBars)?true:na):na, title="Setup Count Down 12", char="C", color=scdpColor, location=scdpLoc, size=scdpSize, transp=Transp, editable=PlotEditEnable)
plotchar(SetupShowCount?((setupCountDown==13)and(13<=SetupBars)?true:na):na, title="Setup Count Down 13", char="D", color=scdpColor, location=scdpLoc, size=scdpSize, transp=Transp, editable=PlotEditEnable)
// plotchar(SetupShowCount?((setupCountDown==14)and(14<=SetupBars)?true:na):na, title="Setup Count Down 14", char="E", color=scdpColor, location=scdpLoc, size=scdpSize, transp=Transp, editable=PlotEditEnable)
// plotchar(SetupShowCount?((setupCountDown==15)and(15<=SetupBars)?true:na):na, title="Setup Count Down 15", char="F", color=scdpColor, location=scdpLoc, size=scdpSize, transp=Transp, editable=PlotEditEnable)
plotshape(SetupShowCount?((setupCountDown>SetupBars)?true:na):na, title="Setup Count Down > Last",  
   text=scdglpText, style=scdglpStyle, color=scdglpColor, location=scdglpLoc, size=scdglpSize, transp=Transp, editable=PlotEditEnable)
