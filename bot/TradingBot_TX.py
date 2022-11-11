'''
[已完工]
從config.cfg讀取帳戶密碼
讀取歷史K線加上自組K線
自組K線與歷史K線的比較
市場收盤時要收K線
運用telegram通知自己已下單訊息與目前設定
修正指標慢了一根K線
獨立使用_RSI策略集
自動選擇周選合約，用TX[tx]的方式，把所有snapshot讀入，只留一定價格以下的，然後排序取最小的。8/31 W6? 9W1，修正錯誤
先訂閱ticks在讀入kbar，然後kbar完成後再接上去
休市期間不要重組K線
訂單訊息檔readOrder
周選下範圍市價單與限價單
函式化
自動交易
報表，使用trade dict:reference IB API new design
上github與別人交流
交易紀錄存在CSV可以延續不因程式中斷而重新計算
加上60分鐘線telegram提醒
沒有小時訊號
刪除df0節省記憶體
週一一早第一根K線有問題
增加大週期：三週期
修正大盤為期指作為履約標的
長週期指標變了telegram提醒
增加是否自動出場開關
增加選擇幾個週期濾網
開盤第一根K線怪怪的，似乎把盤前搓合的合併了。比對歷史K線看看:2022-10-12 08:45:00 Market:Opened 3K Bar:2022-10-12 08:42
收盤沒有收K線
前一天假日沒資料：檢測前一天日期是否存在，如果沒有就一直到有日期的那天抓資料。
即時大週期K線指標
停損:半價/用期貨的前高前低


[問題]
沒下單
資料沒有繼續進來
觸價突破單:邏輯不完整
停損單出場要另外寫，使用範圍市價
tradeRecord要都在place_cb寫，甚至讀取卷商的就好

[未完工]
測試api.list_trades()/api.update_status(api.futopt_account)
有部位/有掛單時不下單
有部位->有掛單->取消掛單或修改掛單或維持
有成交單->還有掛單->取消掛單或修改掛單或維持、設停損停利、平倉條件、取消相對邊掛單、移動停損、加碼
處理OrderState，Live從API回報了解庫存，未成交單子處理:openOrder,closedOrder,openPosition,openOrder,closedOrder,closedPosition
尾隨停損
增加alert。切換DEMO,LIVE,ALERT
在call-back函數之外再建立執行緒來計算

彙整修正同向的提醒
加碼
參考大大的程式
三重濾網
績效統計：勝率、賠率、破產率、平均獲利、平均損失、95%都在多少損失內
接上callback 函數作為回測
即時回測
選擇權的報價
tradingview來啟動 to IB&SinoPac API.
周選合約裡面找划算的
交易股票期貨、選擇權
交易ETF

Snapshot to DataFrame¶


'''
from asyncore import loop
import sys
import os
sys.path.append('/Users/apple/Documents/code/PythonX86/ShioajiAPI')
import requests
from _RSI import *
import shioaji as sj
import configparser
import pandas as pd
import datetime as dt
from datetime import datetime
from datetime import timedelta
import calendar
import time
from threading import Event
import csv
import math

# 建立 Shioaji api 物件
api = sj.Shioaji()

def readConfig():
    global config
    global PI
    global PWD
    global CAPath
    global CAPWD

    config = configparser.ConfigParser()
    config.read('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Settings/config.cfg')  # 讀入個人資料
    PI = str(config.get('Login', 'PersonalId'))
    PWD = str(config.get('Login', 'PassWord'))
    CAPath = str(config.get('Login', 'CAPath'))
    CAPWD = str(config.get('Login', 'CAPassWord'))
    
    
    return

def Tradingsettings():
    global timeFrame1
    global timeFrame2
    global timeFrame3
    global nDollar
    global ifTF2
    global ifTF3
    global ifAutoExit
    global timeFrame1Pre
    global timeFrame2Pre
    global timeFrame3Pre
    global nDollarPre
    global ifAutoExitPre
    global ifCloseBar
    global ifCloseBarPre
    
    config = configparser.ConfigParser()
    config.read('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Settings/TradeSettings.cfg')  # 讀入交易設定
    try:
        timeFrame1 = int(config.get('Trade', 'timeFrame1')) # 讀入交易設定：小週期K線週期
    except:
        pass
    try:
        # timeFrame2 = int(config.get('Trade', 'timeFrame2')) # 讀入交易設定：中週期K線週期
        timeFrame2 = config.get('Trade', 'timeFrame2') # 讀入交易設定：中週期K線週期
    except:
        pass
    try:
        # timeFrame3 = int(config.get('Trade', 'timeFrame3')) # 讀入交易設定：中週期K線週期
        timeFrame3 = config.get('Trade', 'timeFrame3') # 讀入交易設定：中週期K線週期
    except:
        pass

    nDollar = int(config.get('Trade', 'nDollar'))   # 讀入交易設定：選擇權在多少錢以下
    # ifTF2 = bool(config.get('Trade', 'ifTF2'))   # 讀入交易設定：選擇權在多少錢以下
    # ifTF3 = bool(config.get('Trade', 'ifTF3'))   # 讀入交易設定：選擇權在多少錢以下
    ifAutoExit = eval(config.get('Trade', 'ifAutoExit'))   # 讀入交易設定：選擇權在多少錢以下
    ifCloseBar = eval(config.get('Trade', 'ifCloseBar'))   # 讀入交易設定：選擇權在多少錢以下
    
    ifTF2=True if timeFrame2.isdigit() else False
    ifTF3=True if timeFrame3.isdigit() else False
    ifTF3=False if not ifTF2 else ifTF3
    
    
    # 記錄原值做比較是否改變，有則提醒
    timeFrame1Pre=timeFrame1
    timeFrame2Pre=timeFrame2
    timeFrame3Pre=timeFrame3
    nDollarPre=nDollar
    ifAutoExitPre=ifAutoExit
    ifCloseBarPre=ifCloseBar
    return

# 讀取config
readConfig()
Tradingsettings()
# print('start',ifAutoExit)

# 登入帳號
api.login(
    person_id=PI,
    passwd=PWD,
    contracts_cb=lambda security_type: print(
        f"{repr(security_type)} fetch done.")
)

# 匯入憑證
api.activate_ca(
    ca_path=CAPath,
    ca_passwd=CAPWD,
    person_id=PI,
)

# 基本設定
# 呼叫策略函式
StrategyType = 'API'  # 告訴策略用API方式來處理訊號
st = Strategies(StrategyType)   # 策略函式
rm = RiskManage(StrategyType, 2)    # 風控函式

# 2022年休市日期
holidays_list=['1/1','1/26','1/31','2/1','2/2','2/3','2/4','2/7','2/28','4/4','4/5','5/1','5/2','6/3','9/9','9/10','10/10']

# K線重組字典
resDict = {
    'Open': 'first',
    'High': 'max',
    'Low': 'min',
    'Close': 'last'
}

# 從合約讀取選擇權形式字典
optionDict = {'OptionRight.Call': 'Call', 'OptionRight.Put':'Put'}

def readTelegram():
    global config
    global token
    global chatid
    
    config.read(
    '/Users/apple/Documents/code/PythonX86/ShioajiAPI/Settings/TelegramConfig.cfg')
    token = config.get('Section_A', 'token')
    chatid = config.get('Section_A', 'chatid')
    return

# 讀入telegram資料
readTelegram()

# 訂單設定
def readOrder():
    global direction
    global accountType
    global qty
    global directionPre
    global accountTypePre
    global qtyPre
    global orderCount
    # 讀入訂單設定檔
    df_order = pd.read_csv(
        '//Users/apple/Documents/code/PythonX86/ShioajiAPI/Settings/order.csv',index_col=False)
    df_order = df_order.values.tolist()
    a = df_order[0][0].split()
    orderCount=int(a[0])    #下單的次數限制
    
    direction = a[1].upper()    #操作的方向：多、空
    if direction not in ['BUY', 'SELL','WAIT','AUTO']:
        print('Wrong Action!!!')
        c = input('___________________')

    qty = int(a[2]) #下單的數量
    if qty == 0:
        accountType = 'DEMO'    #模擬操作
        qty = 1
    else:
        accountType = 'LIVE'    #實盤操作
        
    # 記錄原值做比較是否改變，有則提醒
    accountTypePre=accountType
    directionPre=direction
    qtyPre=qty
    

    return


# 發送訊息到Telegram函式
def sendTelegram(text, token, chatid):
    text='SinaPac: '+text
    params = {'chat_id': chatid, 'text': text, 'parse_mode': 'HTML'}
    resp = requests.post(
        'https://api.telegram.org/bot{}/sendMessage'.format(token), params)
    resp.raise_for_status()
    return

# 通知下單設定改變
def settingChange():
    global direction
    global accountType
    global qty
    global directionPre
    global accountTypePre
    global qtyPre
    global timeFrame1
    global timeFrame2
    global timeFrame3
    global timeFrame1Pre
    global timeFrame2Pre
    global timeFrame3Pre
    global nDollar
    global nDollarPre
    global ifAutoExit
    global ifAutoExitPre
    global ifCloseBar
    global ifCloseBarPre
    
    
    if (qtyPre!=qty) or (directionPre!=direction) or (accountTypePre!=accountType):
        print('Setting:',accountType,'account',direction,qty)
        sendTelegram('Setting:'+accountType+' account '+direction+' '+str(qty), token, chatid)
        accountTypePre=accountType
        qtyPre=qty
        directionPre=direction
        
    if (timeFrame1!=timeFrame1Pre) or (timeFrame2!=timeFrame2Pre) or (timeFrame3!=timeFrame3Pre) :
        print('Time Frame change',timeFrame1,timeFrame2,timeFrame3)
        sendTelegram('Time Frame change:'+str(timeFrame1)+' '+str(timeFrame2)+' '+str(timeFrame3), token, chatid) 
        timeFrame1Pre=timeFrame1   
        timeFrame2Pre=timeFrame2   
        timeFrame3Pre=timeFrame3   
    
    if (nDollar!=nDollarPre): 
        print('Contract blew ',nDollar)
        sendTelegram('Contract blew '+str(nDollar), token, chatid)  
        nDollarPre=nDollar   
    
    if (ifAutoExit!=ifAutoExitPre):
        print('Auto Exit is',ifAutoExit)
        sendTelegram('Auto Exit is  '+str(ifAutoExit), token, chatid)  
        ifAutoExitPre=ifAutoExit
    
    if (ifCloseBar!=ifCloseBarPre):
        print('If act at HTF Bar closed',ifCloseBar)
        sendTelegram('If act at HTF Bar closed '+str(ifCloseBar), token, chatid)  
        ifCloseBarPre=ifCloseBar
        
    return

# 根據當前日期選擇近月合約：結算日則以次月合約
def selectFutures():
    global futureSymbol
    year = datetime.now().year  # 今年
    month =datetime.now().month  # 這個月
    day=21-(dt.date(year,month,1).weekday()+4)%7         #   weekday函數 禮拜一為0;禮拜日為6
    
    if datetime.now().day>=day:     #計算下個月結算日
        month=month+1
        day=21-(dt.date(year,month,1).weekday()+4)%7 
   
    futureSymbol='TXF'+str(year)+str(month).zfill(2) #zfill(2)保持月份是兩位數
    print(futureSymbol,'Settlement date is',dt.date(year,month,day))
    contract=api.Contracts.Futures['TXF'][futureSymbol]
    return contract


# 從CSV讀入交易紀錄
def fromCSV():
    dict_tradeRecord={}
    list_openTrade=[]
    
    if not os.path.isfile('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/tradeRecord.csv'):
        # print({},[])
        return {},[]
    elif os.path.isfile('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/tradeRecord.csv') and not os.path.isfile('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/openTrade.csv'):
        df_tradeRecord=pd.read_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/tradeRecord.csv',index_col=0)
        for index in df_tradeRecord.index:
            dict_tradeRecord[df_tradeRecord.loc[index,'DateTime']]=df_tradeRecord.loc[index].to_dict()
            # dict_tradeRecord.drop(index=dict_tradeRecord[dict_tradeRecord['Exit Price']==0].index,axis = 0,inplace = True)
        # print(dict_tradeRecord,[])
        return dict_tradeRecord,[]
    elif os.path.isfile('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/tradeRecord.csv') and os.path.isfile('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/openTrade.csv'):
        df_tradeRecord=pd.read_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/tradeRecord.csv',index_col=0)
        for index in df_tradeRecord.index:
            dict_tradeRecord[df_tradeRecord.loc[index,'DateTime']]=df_tradeRecord.loc[index].to_dict()
            # dict_tradeRecord.drop(index=dict_tradeRecord[dict_tradeRecord['Exit Price']==0].index,axis = 0,inplace = True)
        try:
            df_openTrade=pd.read_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/openTrade.csv')
            # df_openTrade=pd.read_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/openTrade.csv',index=0)
        except:
            # print(dict_tradeRecord,[])
            return dict_tradeRecord,[]
        list_openTrade=df_openTrade.loc[0].to_list()
        # print(dict_tradeRecord,list_openTrade)
        return dict_tradeRecord,list_openTrade
    
# 檢查是否為休市期間
def ifOffMarket():
    global holidays_list
    # print('1',(datetime.now().strftime('%H:%M') >'05:00' and datetime.now().strftime('%H:%M') < '08:45'),'2',(datetime.now().strftime('%H:%M') > '13:45' and datetime.now().strftime('%H:%M') < '15:00'),'3',(datetime.now().isoweekday() in [6, 7]),'4',((datetime.now().strftime('%H:%M') >'05:00' and datetime.now().strftime('%H:%M') < '08:45') or (datetime.now().strftime('%H:%M') > '13:45' and datetime.now().strftime('%H:%M') < '15:00') or datetime.now().isoweekday() in [6, 7] ))
    
    return (datetime.now().strftime('%H:%M') >'05:00' and datetime.now().strftime('%H:%M') < '08:45') or (datetime.now().strftime('%H:%M') > '13:45' and datetime.now().strftime('%H:%M') <'15:00') or datetime.now().isoweekday() in [7] or datetime.now().strftime('%m/%d') in holidays_list



offMarket =ifOffMarket()   # 是否交易時間之外
placedOrder = 0  # 一開始下單次數為零
ifStopOut=False # 判斷是否停損初始值
 
#依照設定來動作
readOrder()
settingChange()

# 模擬賬戶紀錄
tradeRecord={}
openTrade=[]    #紀錄未平倉
openOrder=pd.DataFrame([], columns = ['ts','order_id','order_seqno','order_ordno','Account Type'])   #紀錄未成交
# fromCSV(tradeRecord,openTrade)
# 合約設定
contract_txf = selectFutures()  # 選定期指合約
# 讀入過去交易紀錄
tradeRecord,openTrade=fromCSV()

# 訂閱即時ticks資料
api.quote.subscribe(contract_txf)  
today=datetime.now().strftime('%F')
beforeYesterday=(datetime.now()-timedelta(days=1)) # 抓取昨日資料的資料量足夠產生訊號 
offMarketDay=beforeYesterday.isoweekday() in [7] or beforeYesterday.strftime('%m/%d') in holidays_list 

# 如果昨天休市往前一直找到非休市日
ds=1
while offMarketDay:
    beforeYesterday=(datetime.now()-timedelta(days=ds))
    offMarketDay=beforeYesterday.isoweekday() in [7] or beforeYesterday.strftime('%m/%d') in holidays_list 
    ds+=1
beforeYesterday=beforeYesterday.strftime('%F')

# 讀入歷史1分K
kbars = api.kbars(contract_txf, start=beforeYesterday, end=today)  # 讀入歷史1分K
# kbars = api.kbars(contract_txf)  
df0 = pd.DataFrame({**kbars})  # 先將Kbars物件轉換為Dict，再傳入DataFrame做轉換
df0.ts = pd.to_datetime(df0.ts)  # 將原本的ts欄位中的資料，轉換為DateTime格式並回存
df0.index = df0.ts  # 將ts資料，設定為DataFrame的index

# 重組1分線為小週期Ｋ線
df1 = df0.resample(str(timeFrame1)+'min', closed='left',label='left').agg(resDict)  
df1.reset_index(inplace=True)
# 重組1分線為中週期Ｋ線
df2 = df0.resample(str(timeFrame2)+'min', closed='left',label='left').agg(resDict)  
df2.reset_index(inplace=True)
# 重組1分線為大週期Ｋ線
df3 = df0.resample(str(timeFrame3)+'min', closed='left',label='left').agg(resDict)  
df3.reset_index(inplace=True)
# 刪除1分鐘線節省記憶體
df0.drop(df0.index, inplace=True)

# 紀錄時間的Flag確保只進行一次比對
nextMinute1 = int(datetime.now().minute)  
nextMinute2 = datetime.now().strftime('%H:%M')  
nextMinute3 = datetime.now().strftime('%H:%M') 


# 紀錄ticks
data1 = []  

# 去掉交易時間外的空行，重置index保持連續避免dataframe操作錯誤
df1.dropna(axis=0, how='any', inplace=True)  
df1.reset_index(drop=True)   
df2.dropna(axis=0, how='any', inplace=True)  
df2.reset_index(drop=True)   
df3.dropna(axis=0, how='any', inplace=True)
df3.reset_index(drop=True) 



# 儲存df檢查正確性
# df1.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/df1.csv',index=1)
# df2.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/df2.csv',index=1)
# df3.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/df3.csv',index=1)


# 檢查大週期的多空
if ifTF2:
    direction2=st._RSI_HTF(df2,timeFrame2)
    direction2_pre=direction2
    print(datetime.fromtimestamp(int(datetime.now().timestamp())),timeFrame2,direction2)
    if ifTF3:
        direction3=st._RSI_HTF(df3,timeFrame3)
        direction3_pre=direction3
        print(datetime.fromtimestamp(int(datetime.now().timestamp())),timeFrame2,direction2,timeFrame3,direction3)
        all_timeframes=pd.DataFrame([], columns = ['Symbol', str(timeFrame2),str(timeFrame3)]) 
        all_timeframes.loc[0]=futureSymbol,direction2,direction3
        all_timeframes.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/all_timeframes.csv',index=0)
    else:
        all_timeframes=pd.DataFrame([], columns = ['Symbol', str(timeFrame2)]) 
        all_timeframes.loc[0]=futureSymbol,direction2
        all_timeframes.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/all_timeframes.csv',index=0)
else:
    all_timeframes=pd.DataFrame([]) 
    all_timeframes.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/all_timeframes.csv',index=0)

# 選定選擇權合約
def selectOption():
    '''
    需要把所有大盤上下10檔都snapshop出報價來選擇一定價格以下的合約
    '''
    global orderPrice
    global df1
    
    
    # 計算今年每個月的結算日
    year = datetime.now().year
    month = datetime.now().month
    day = datetime.now().day
    settleDict={}   # 紀錄今年所有月份的結算日
    sday=0  #本月第一個週三是幾日
    for month in range(1,13):
        weekday=dt.date(year,month,1).isoweekday()  # 計算每個月1日為週幾
        weeks=0
        settleDict[month]={}
        
        #第一個週三為幾日
        if weekday>3:
            sday=1+10-weekday   
        elif weekday <=3:
            sday=1+3-weekday
        for n in range(0,5):
            weeks=n+1
            
            if sday+n*7>calendar.monthrange(year, month)[1] :   #以每月最後一日為限計算有幾個週三
                pass  
            else:
                settleDict[month][n+1]=dt.datetime(year,month,sday+n*7,8,45,0).strftime("%F %H:%M:%S")  # 紀錄每個月結算日
                
    for m in settleDict.keys():
        for w in settleDict[m].keys():
            
            # 今年的結算日中如果找到大於今天則跳出所有迴圈，取最接近今天的結算日
            if settleDict[m][w]>datetime.now().strftime("%F %H:%M:%S"): #比對哪個週結算日超過目前日期，此為最近的週結算日
                month=m
                weeks=w
                break   
        else:
            continue
        break
    
    #計算履約價與合約價，依照大盤期指轉換每50點間隔的履約價
    for count in range(1, 41):
        if direction.upper() == 'BUY':
            strikePrice = str(
                int(df1.loc[df1.index[-1],'Close']-df1.loc[df1.index[-1],'Close'] % 50+count*50))+'C'
        elif direction.upper() == 'SELL':
            strikePrice = str(
                int(df1.loc[df1.index[-1],'Close']-df1.loc[df1.index[-1],'Close'] % 50-(count-1)*50))+'P'
        
        # 算出TX?
        tx = 'TX'+str(weeks) if weeks != 3 else 'TXO'  
        
        # 算出當前日期適合的合約symbol
        sym=tx+str(year)+str(month).zfill(2)+strikePrice    
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),sym)
        
        
        try:
            # 取得合約的價格
            contract=symbol2Contract(sym)
            snapshots = api.snapshots([contract])
            orderPrice = int(snapshots[0].close)  
        
            print(datetime.fromtimestamp(int(datetime.now().timestamp())),sym, orderPrice)
            
            # 取得nDollar元以下最接近nDollar元的合約
            if orderPrice <= nDollar:  
                return contract
            tmpContract = contract
        except:
            pass
    
    #如果沒有滿足nDollar以下的合約則以最接近的合約
    contract = tmpContract  
    print(datetime.fromtimestamp(int(datetime.now().timestamp())),'tmpContract:', sym, price)

    return contract

# 將訂閱報價合約中的code轉為symbol
def code2symbol(code):
    callDict={'A':'01','B':'02','C':'03','D':'04','E':'05','F':'06','G':'07','H':'08','I':'09','J':'10','K':'11','L':'12'}
    putDict={'M':'01','N':'02','O':'03','P':'04','Q':'05','R':'06','S':'07','T':'08','U':'09','V':'10','W':'11','X':'12'}
    if code[8] in callDict.keys():
        sym=code[:3]+str(2020+int(code[-1]))+callDict[code[8]]+code[3:8]+'C'
    elif code[8] in putDict.keys():
        sym=code[:3]+str(2020+int(code[-1]))+putDict[code[8]]+code[3:8]+'P'
    else:
        print('error code')
    return sym

# 列出期貨部位
def get_positions():
    global df_positions     
    positions = api.list_positions(api.futopt_account)
    df_positions = pd.DataFrame(p.__dict__ for p in positions)
    df_positions.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/positions.csv',index=0)

    return

# 接收tick報價
@api.quote.on_quote
def q(topic, quote):
    global accountType
    global nextMinute1
    global nextMinute2
    global nextMinute3
    global df1
    global df2
    global df3
    global data1
    global closePrice
    global contract_txo
    global tradeRecord
    global timeFrame1
    global timeFrame2
    global timeFrame3
    global timeFrame1Pre
    global timeFrame2Pre
    global timeFrame3Pre
    global openTrade
    global openOrder
    global optionDict
    global direction
    global direction2
    global direction3
    global direction2_pre
    global direction3_pre
    global ifTF2
    global ifTF3
    global offMarket
    global nDollar
    global nDollarPre
    global ifAutoExit
    global ifAutoExitPre
    global ifCloseBar
    global ifCloseBarPre
    global ifStopOut
    global today
    global beforeYesterday
    global trade
    global SL
    global TP
    global BP
    global df_positions
    
    conditionBuy=False
    conditionSell=False
    
    ts = pd.Timestamp(quote['Date']+' '+quote['Time'][:8])  # 讀入Timestamp
    close = quote['Close'][0] if isinstance(
        quote['Close'], list) else quote['Close']  # 放入tick值
    
    # Timestamp在timeFrame1或timeFrame1的倍數時以及收盤時進行一次tick重組分K
    offMarket =ifOffMarket()   # 是否交易時間之外
    if not offMarket:
        data1.append([ts, close])
        # 測試ticks接收
        # dfTick = pd.DataFrame(data1,columns=['ts','Close'])
        # dfTick.ts = pd.to_datetime(dfTick.ts)
        # dfTick.index = dfTick.ts
        # dfTick.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/dfTick.csv',index=0)
    
    # 判斷是否小週期收K線
    if (not offMarket and ts.minute/timeFrame1 == ts.minute//timeFrame1 and nextMinute1 != ts.minute and datetime.now().isoweekday() in [1,2,3,4,5,6]) or (datetime.now().strftime('%H:%M') in ['13:45', '05:00'] and nextMinute1 != ts.minute and datetime.now().isoweekday() in [1,2,3,4,5,6]):
        nextMinute1 = ts.minute  # 相同的minute1分鐘內只重組一次
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),
        #       'Market:Closed.' if offMarket else 'Market:Opened Bar Label:'+ts.strftime('%F %H:%M'))
        resampleBar(timeFrame1, data1)  # 重組K線
        
        
        unixtime = time.mktime(ts.timetuple())
        # print(unixtime/(timeFrame2*60),unixtime//(timeFrame2*60),datetime.now().timestamp(),unixtime,ts)

        # 進場訊號
        signalEntry = st._RSI_SMA(df1)
        
        # 出場訊號
        signalExit = st._RSI(df1)
        
        # 期貨的停損價
        SL=rm.SL(df1,signalEntry)
        
        # 期貨的突破價
        BP=st._BP(df1,direction)
        
        #--------------------------
        # 列出期貨部位
        get_positions()
        if not df_positions.empty:
            tradeRecord[list(tradeRecord.keys())[-1]]['Unrealized PNL']
        
        # 查詢帳戶餘額
        # accountBalance = api.account_balance()   
        # df_accountBalance = pd.DataFrame(accountBalance)  
        # df_accountBalance.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/accountBalance.csv',index=0)
           
           
        # 列出平倉
        # settlement = api.settlements(api.futopt_account)
        # df_settlement=pd.DataFrame(s.__dict__ for s in settlement).set_index("T")  
        # df_settlement.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/settlement.csv',index=0)

        
        #-------------------------
        
    
        # 列出簡要損益
        # profitloss_sum = api.list_profit_loss_sum(api.futopt_account,beforeYesterday,today)
        # df_profitloss_sum = pd.DataFrame(data.__dict__ for data in profitloss_sum.profitloss_summary) 
        # df_profitloss_sum.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/profitloss_sum.csv',index=0)
        
        # 列出平倉損益
        # pl=api.list_profit_loss_detail(api.futopt_account,2)
        # df_pl = pd.DataFrame(pl)
        # df_pl.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/pl.csv',index=0)

        # 列出損益
        profitloss = api.list_profit_loss(api.futopt_account,beforeYesterday,today) 
        df_profitloss = pd.DataFrame(p.__dict__ for p in profitloss)
        df_profitloss.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/profitloss.csv',index=0)

        
        # 查詢現有部位
        # openPosition=api.get_account_openposition(product_type='2', query_type='0', account=api.futopt_account)
        # print(openPosition)
        # df_openPosition = pd.DataFrame(p.__dict__ for p in openPosition)
        # df_openPosition.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/openPosition.csv',index=0)

        # df_openPosition = pd.DataFrame(openPosition)
        # df_openPosition.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/accountBalance.csv',index=0)
           
        
        # 查詢保證金
        # margin = api.margin(api.futopt_account) 
        # margin = api.get_account_margin(api.futopt_account) 
        # df_margin = pd.DataFrame(p.__dict__ for p in margin)
        # df_margin.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/margin.csv',index=0)

        
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),margin)
 

        # 大週期即時K線
        if not ifCloseBar:
        
            df2=df1.set_index('ts').resample(str(timeFrame2)+'min', closed='left', label='left').agg(resDict)
            df2.dropna(axis=0, how='any', inplace=True)  
            df2.reset_index(drop=True)
            direction2=st._RSI_HTF(df2,timeFrame2)
            
            df3=df1.set_index('ts').resample(str(timeFrame3)+'min', closed='left', label='left').agg(resDict)
            df3.dropna(axis=0, how='any', inplace=True)  
            df3.reset_index(drop=True)
            direction3=st._RSI_HTF(df3,timeFrame3)
        
        
        # 判斷是否中週期收K線
        elif ifTF2:
            if (ts.minute/int(timeFrame2) == ts.minute//int(timeFrame2) and nextMinute2 != ts.strftime('%H:%M')):
                # print(int(datetime.now().timestamp()/(timeFrame2*60))-int(unixtime/(timeFrame2*60)))
                nextMinute2 = ts.strftime('%H:%M')  # 相同的minute1分鐘內只重組一次
                df_res2=df1.copy()
                df_res2.ts = pd.to_datetime(df_res2.ts)  # 將原本的ts欄位中的資料，轉換為DateTime格式並回存
                df_res2.index = df_res2.ts  # 將ts資料，設定為DataFrame的index
                df2 = df_res2.resample(str(timeFrame2)+'min', closed='left',label='left').agg(resDict)  # 將1分K重組成中週期分K
                # df2.reset_index(inplace=True)
                # df1.reset_index(inplace=True)
                df2.dropna(axis=0, how='any', inplace=True)  # 去掉交易時間外的空行
                # df2.reset_index(drop=True)   # 重置index保持連續避免dataframe操作錯誤
                df2.reset_index(drop=True)
                # print(df2.tail(3))
                # df2.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/df2.csv',index=1)
                
                # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Market:Closed.' if offMarket else 'Market:Opened',str(timeFrame2)+'K Bar:'+df2.index[-1].strftime('%F %H:%M'))

                
                # 檢查收K線之後大週期的多空
                direction2=st._RSI_HTF(df2,timeFrame2)
                if direction2!=direction2_pre:
                    if ifTF3:
                        print(datetime.fromtimestamp(int(datetime.now().timestamp())),'['+str(timeFrame2)+']',direction2,timeFrame3,direction3)
                        if direction==direction2 and direction2==direction3:
                            print(datetime.fromtimestamp(int(datetime.now().timestamp())),'All direction:',direction)
                            sendTelegram('All direction: '+direction,token,chatid)
                            all_timeframes.loc[0]=direction2,direction3
                            all_timeframes.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/all_timeframes.csv',index=0)
                    else:
                        print(datetime.fromtimestamp(int(datetime.now().timestamp())),'['+str(timeFrame2)+']',direction2)
                        if direction==direction2:
                            print(datetime.fromtimestamp(int(datetime.now().timestamp())),'All direction:',direction)
                            sendTelegram('All direction: '+direction,token,chatid)
                            all_timeframes.loc[0]=direction2
                            all_timeframes.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/all_timeframes.csv',index=0)
                    direction2_pre=direction2
                
                # 判斷是否大週期收K線
                if ifTF3:
                    if (ts.minute/int(timeFrame3) == ts.minute//int(timeFrame3) and nextMinute3 != ts.strftime('%H:%M')):
                        # print(timeFrame3)
                        nextMinute3 = ts.strftime('%H:%M')  # 相同的minute1分鐘內只重組一次
                        df_res3=df1.copy()
                        df_res3.ts = pd.to_datetime(df_res3.ts)  # 將原本的ts欄位中的資料，轉換為DateTime格式並回存
                        df_res3.index = df_res3.ts  # 將ts資料，設定為DataFrame的index
                        df3 = df_res3.resample(str(timeFrame3)+'min', closed='left',label='left').agg(resDict)  # 將1分K重組成中週期分K
                        # df2.reset_index(inplace=True)
                        # df1.reset_index(inplace=True)
                        df3.dropna(axis=0, how='any', inplace=True)  # 去掉交易時間外的空行
                        # df2.reset_index(drop=True)   # 重置index保持連續避免dataframe操作錯誤
                        df3.reset_index(drop=True)
                        # print(df2.tail(3))
                        # df3.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/df3.csv',index=1)
                        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Market:Closed.' if offMarket else 'Market:Opened',str(timeFrame3)+'K Bar:'+df3.index[-1].strftime('%F %H:%M'))

                        # 檢查收K線之後大週期的多空
                        
                        direction3=st._RSI_HTF(df3,timeFrame3)
                        
                        
                        if direction3!=direction3_pre:
                            print(datetime.fromtimestamp(int(datetime.now().timestamp())),timeFrame2,direction2,'['+str(timeFrame3)+']',direction3)
                            sendTelegram(str(timeFrame3)+' min '+direction3,token,chatid)
                            all_timeframes.loc[0]=direction2,direction3
                            all_timeframes.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/all_timeframes.csv',index=0)
                            direction3_pre=direction3
                            if direction==direction2 and direction2==direction3:
                                print(datetime.fromtimestamp(int(datetime.now().timestamp())),'All direction:',direction)
                                sendTelegram('All direction: '+direction,token,chatid)  
        
        # 判斷買進條件
        if ifTF2 and ifTF3:
            conditionBuy=signalEntry =='BUY' and direction2!='SELL' and direction3!='SELL'
            conditionSell=signalEntry =='SELL' and direction2!='BUY' and direction3!='BUY'
        elif ifTF2:
            conditionBuy=signalEntry =='BUY' and direction2!='SELL' 
            conditionSell=signalEntry =='SELL' and direction2!='BUY'
            # print('conditionBuy:',conditionBuy,'signalEntry==BUY',signalEntry =='BUY','direction2!=SELL:',direction2!='SELL')
            # print('conditionSell:',conditionSell,'signalEntry==SELL',signalEntry =='SELL','direction2!=BUY:',direction2!='BUY')
        else:
            conditionBuy=signalEntry =='BUY'
            conditionSell=signalEntry =='SELL'
            
        #依照設定更改動作
        readOrder()
        Tradingsettings()
        settingChange()
        
        # Buy call訊號處理
        if direction=='BUY':  
            # 是否停損
            if accountType=='DEMO' and len(openTrade)!=0:
                ifStopOut=(close<tradeRecord[openTrade[0]]['SL'])
                if ifStopOut:
                    print(datetime.fromtimestamp(int(datetime.now().timestamp())),tradeRecord[openTrade[0]]['Symbol']+'停損：','價位：',close,'停損價：',tradeRecord[openTrade[0]]['SL'])
            else:
                ifStopOut=False
                
            if accountType=='LIVE' and not df_positions.empty:
                ifStopOut=(close<tradeRecord[list(tradeRecord.keys())[-1]]['SL'])
                if ifStopOut:
                    print(datetime.fromtimestamp(int(datetime.now().timestamp())),close<tradeRecord[list(tradeRecord.keys())[-1]]['Symbol']+'停損：','價位：',close,'停損價：',close<tradeRecord[list(tradeRecord.keys())[-1]]['SL'])
            else:
                ifStopOut=False
                
            # if conditionBuy or (close>BP and BP!=0) :  #進場訊號 
            if conditionBuy:  #進場訊號 
                # if len(openTrade)==0 and openOrder.empty: # 沒有未平倉部位與未成交訂單
                if len(openTrade)==0 and df_positions.empty: # 沒有未平倉部位與未成交訂單
                    contract_txo = selectOption()   #選擇選擇權合約
                    snapshots = api.snapshots([contract_txo])  # 取得合約的snapshots
                    closePrice = snapshots[0].close #取得合約價格
                    # order = selectOrder(signalEntry,qty) #設定訂單
                    order = selectOrder('BUY',qty) #設定訂單
                    placeOrder(contract_txo, order) #下單
                    
                    # 紀錄模擬交易紀錄
                    if accountType=='DEMO':
                        tradeRecord[ts.strftime('%F %H:%M:%S')]={
                                                            'Account Type':accountType,
                                                            'Symbol':contract_txo.symbol,
                                                            'DateTime':ts.strftime('%F %H:%M:%S'),
                                                            'Entry Price':closePrice,
                                                            'Exit Price':0.,
                                                            'Exit DateTime':'',
                                                            'Quantity':qty,
                                                            'Unrealized PNL':0.,
                                                            'Realized PNL':0.,
                                                            'Commision':18*qty,
                                                            'Tax':math.ceil(closePrice*50*0.001*qty),
                                                            'SL':SL,
                                                            'TP':0.
                                                            }
                        # 紀錄未平倉紀錄
                        openTrade.append(list(tradeRecord.keys())[-1])
                    
                        # 交易紀錄寫入CSV
                        toCSV(tradeRecord,openTrade)
                    
                elif len(openTrade)!=0 or not df_positions.empty:     #如果未平倉不為零，留作未來加碼用
                    # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'openTrade!=0')

                    pass
            
            
            elif (signalExit=='SELL' and ifAutoExit) or ifStopOut: 
                if len(openTrade)!=0 or not df_positions.empty:  #模擬單或實單有部位
                    
                    if len(openTrade)!=0:
                        contract_txo = symbol2Contract(tradeRecord[openTrade[0]]['Symbol']) #讀取部位合約
                    elif not df_positions.empty:
                        contract_txo = symbol2Contract(tradeRecord[list(tradeRecord.keys())[-1]]['Symbol']) #讀取部位合約
                        
                    snapshots = api.snapshots([contract_txo])  # 取得合約的snapshots
                    closePrice = snapshots[0].close #取得目前合約價
                    
                    if len(openTrade)!=0:
                        order = selectOrder('SELL',tradeRecord[openTrade[0]]['Quantity'])   #設定平倉訂單
                    elif not df_positions.empty:
                        order = selectOrder('SELL',tradeRecord[list(tradeRecord.keys())[-1]]['Quantity'])   #設定平倉訂單
                    placeOrder(contract_txo, order) #下單
                    
                    # 判別模擬單或實單做交易紀錄
                    if accountType=='DEMO':
                        tradeRecord[openTrade[0]]['Exit Price']=closePrice  #紀錄出場價格
                        tradeRecord[openTrade[0]]['Exit DateTime']=datetime.fromtimestamp(int(datetime.now().timestamp()))  #紀錄出場時間
                        tradeRecord[openTrade[0]]['Commision']=tradeRecord[openTrade[0]]['Commision']+18*tradeRecord[openTrade[0]]['Quantity']  #紀錄手續費
                        tradeRecord[openTrade[0]]['Tax']=tradeRecord[openTrade[0]]['Tax']+math.ceil(closePrice*50*0.001*tradeRecord[openTrade[0]]['Quantity'])  #紀錄稅
                        tradeRecord[openTrade[0]]['Realized PNL']=round(50*(tradeRecord[openTrade[0]]['Exit Price']-tradeRecord[openTrade[0]]['Entry Price']),0) #紀錄實現利潤
                        tradeRecord[openTrade[0]]['Unrealized PNL']=round(0.0,0) #未平倉損益歸零

                        #清空未平倉紀錄
                        openTrade=[]    
                        
                        # 交易紀錄寫入CSV
                        toCSV(tradeRecord,openTrade)
        
        # elif direction=='SELL' and openOrder.empty:    #buy put
        elif direction=='SELL':    #buy put
            # 是否停損
            if accountType=='DEMO' and len(openTrade)!=0:
                ifStopOut=(close>tradeRecord[openTrade[0]]['SL'])
                if ifStopOut:
                    print(datetime.fromtimestamp(int(datetime.now().timestamp())),tradeRecord[openTrade[0]]['Symbol']+'停損：','價位：',close,'停損價：',tradeRecord[openTrade[0]]['SL'])
            else:
                ifStopOut=False
                
            if accountType=='LIVE' and not df_positions.empty:
                ifStopOut=(close>close<tradeRecord[list(tradeRecord.keys())[-1]]['SL'])
                if ifStopOut:
                    print(datetime.fromtimestamp(int(datetime.now().timestamp())),close<tradeRecord[list(tradeRecord.keys())[-1]]['Symbol']+'停損：','價位：',close,'停損價：',close<tradeRecord[list(tradeRecord.keys())[-1]]['SL'])
            else:
                ifStopOut=False
                
            # if conditionSell or (close<BP and BP!=0):    # 設突破單（未完工） if close>breakOutPrice:
            if conditionSell:    # 設突破單（未完工） if close>breakOutPrice:
                # if len(openTrade)==0 and openOrder.empty: # 沒有未平倉部位與未成交訂單
                if len(openTrade)==0 and df_positions.empty: # 沒有未平倉部位與未成交訂單
                    contract_txo = selectOption()
                    snapshots = api.snapshots([contract_txo])  # 取得合約的snapshots
                    closePrice = snapshots[0].close
                    order = selectOrder('BUY',qty)
                    placeOrder(contract_txo, order)
                    # 判別模擬單或實單做交易紀錄
                    if accountType=='DEMO':
                        tradeRecord[ts.strftime('%F %H:%M:%S')]={
                                                            'Account Type':accountType,
                                                            'Symbol':contract_txo.symbol,
                                                            'DateTime':ts.strftime('%F %H:%M:%S'),
                                                            'Entry Price':closePrice,
                                                            'Exit Price':0.,
                                                            'Exit DateTime':'',
                                                            'Quantity':qty,
                                                            'Unrealized PNL':0.,
                                                            'Realized PNL':0.,
                                                            'Commision':18*qty,
                                                            'Tax':math.ceil(closePrice*50*0.001*qty),
                                                            'SL':SL,
                                                            'TP':0.
                                                            }
                        # 紀錄未平倉紀錄
                        openTrade.append(list(tradeRecord.keys())[-1])
                    
                        # 交易紀錄寫入CSV
                        toCSV(tradeRecord,openTrade)
                    
                elif len(openTrade)!=0 or not df_positions.empty:
                    # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'openTrade!=0')
                    pass
                
            elif (signalExit=='BUY' and ifAutoExit) or ifStopOut:
                if len(openTrade)!=0 or not df_positions.empty:
                    if len(openTrade)!=0:
                        contract_txo = symbol2Contract(tradeRecord[openTrade[0]]['Symbol']) #讀取部位合約
                    elif not df_positions.empty:
                        contract_txo = symbol2Contract(tradeRecord[list(tradeRecord.keys())[-1]]['Symbol']) #讀取部位合約
                    snapshots = api.snapshots([contract_txo])  # 取得合約的snapshots
                    closePrice = snapshots[0].close
                    if len(openTrade)!=0:
                        order = selectOrder('SELL',tradeRecord[openTrade[0]]['Quantity'])   #設定平倉訂單
                    elif not df_positions.empty:
                        order = selectOrder('SELL',tradeRecord[list(tradeRecord.keys())[-1]]['Quantity'])   #設定平倉訂單
                    placeOrder(contract_txo, order)
                    
                    # 判別模擬單或實單做交易紀錄
                    if accountType=='DEMO':
                        tradeRecord[openTrade[0]]['Exit Price']=closePrice
                        tradeRecord[openTrade[0]]['Exit DateTime']=datetime.fromtimestamp(int(datetime.now().timestamp()))  #紀錄出場時間
                        tradeRecord[openTrade[0]]['Commision']=tradeRecord[openTrade[0]]['Commision']+18*tradeRecord[openTrade[0]]['Quantity']
                        tradeRecord[openTrade[0]]['Tax']=tradeRecord[openTrade[0]]['Tax']+math.ceil(closePrice*50*0.001*tradeRecord[openTrade[0]]['Quantity'])
                        tradeRecord[openTrade[0]]['Realized PNL']=round(50*(tradeRecord[openTrade[0]]['Exit Price']-tradeRecord[openTrade[0]]['Entry Price']),0)
                        tradeRecord[openTrade[0]]['Unrealized PNL']=round(0.0,0) #未平倉損益歸零
                        
                        #清空未平倉紀錄
                        openTrade=[]    
                        
                        # 交易紀錄寫入CSV
                        toCSV(tradeRecord,openTrade)   
                        # tradeRecord={}    
                        
        
# 重組ticks轉換5分K
def resampleBar(period,data1):
    global df1
    global offMarket
    df_tick = pd.DataFrame(data1, columns=['ts', 'Close'])  #用來暫存ticks
    df_tick.ts = pd.to_datetime(df_tick.ts)
    df_tick.index = df_tick.ts
    # df_tick.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/df_tick.csv',index=0)
    df_res = df_tick.Close.resample(
        str(period)+'min', closed='left', label='left').agg(resDict)  # tick重組分K
    del data1[0:len(data1)-1]  # 只保留最新的一筆tick，減少記憶體佔用
    df_res.drop(df_res.index[-1], axis=0, inplace=True)  # 去掉最新的一筆分K，減少記憶體佔用
    # print('offMarket',offMarket)
    try:
        print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Market:Closed.' if offMarket else 'Market:Opened',str(timeFrame1)+'K Bar:'+df_res.index[-1].strftime('%F %H:%M'))
    except:
        pass
    df_res.reset_index(inplace=True)
    df_res.dropna(axis=0, how='any', inplace=True)  # 去掉空行
    if len(df_res.ts) != 0 and len(df1.ts) != 0: #當有新的重組K線時
        while df1.iloc[-1, 0] >= df_res.iloc[0, 0]:  #以新的重組K線的資料為主，刪除歷史K線最後幾筆資料
            df1.drop(df1.index[-1], axis=0, inplace=True)
    df1 = pd.concat([df1, df_res], ignore_index=True)  # 重組後分K加入原來歷史分K
    # print(df1)
    df1.reset_index(drop=True)   # 重置index保持連續避免dataframe操作錯誤
    # df1.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/df1.csv',index=1)
    # df_res.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/df_res.csv',index=0)
    return
    
#設定訂單
def selectOrder(action,quantity):
    global contract_txo
    global optionDict
    global closePrice
    global ifStopOut
    
    order = api.Order(
        # 動作,'Buy','Sell'
        action=action.title(),
        
        # 價格
        price=closePrice-5 if ifStopOut and action.title()=='Sell' else closePrice,
        
        # 口數  
        quantity=quantity,  
        
        # LMT:限價單,MKP:範圍市價單
        #  price_type='MKP' if ifStopOut else 'LMT',
        price_type='LMT',
        
        # ROD:當日有效(Rest of Day),IOC:立即成交否則取消(Immediate-or-Cancel),FOK: FOK：全部成交否則取消(Fill-or-Kill)
        # order_type='IOC' if ifStopOut else 'ROD', 
        order_type='ROD', 
        
        # 倉別，使用自動
        octype='Auto',  
        
        #選擇權類型
        OptionRight=optionDict[str(contract_txo.option_right)],  # 選擇權類型,'Call','Put'
        
        # 下單帳戶指定期貨帳戶
        account=api.futopt_account  
    )
    return order

# 發送訂單
def placeOrder(contract_txo, order):
    global accountType
    global placedOrder
    global optionDict
    global orderCount
    global trade
    
    if accountType == 'LIVE':   #實盤時
        if placedOrder <= orderCount:   #在未達限定操作次數時
            # 下單
            trade = api.place_order(contract_txo, order)
            # 顯示訊息
            print(datetime.fromtimestamp(int(datetime.now().timestamp())), accountType,'Account',  order.action.upper(),optionDict[str(contract_txo.option_right)],contract_txo.symbol,'@',str(closePrice))
            
            print('=======trade======')
            print(trade)
            
            '''
            if trade.status.status=='Submitted':
                print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Submitted:傳送成功')
                print(datetime.fromtimestamp(int(datetime.now().timestamp())),trade.status.status)
            if trade=='Cancelled':
                print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Cancelled:已刪除')
                print(datetime.fromtimestamp(int(datetime.now().timestamp())),trade)
            if trade=='Filled':
                print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Filled:完全成交')
                print(datetime.fromtimestamp(int(datetime.now().timestamp())),trade.contract)
                print(datetime.fromtimestamp(int(datetime.now().timestamp())),trade.order)
                print(datetime.fromtimestamp(int(datetime.now().timestamp())),trade.status)
            '''
            
            # 發送telegram
            sendTelegram(accountType+' Account '+ order.action.upper()+' '+optionDict[str(contract_txo.option_right)]+' '+contract_txo.symbol+'@'+str(closePrice), token, chatid)
            placedOrder += 1
            api.list_trades()
            api.update_status(api.futopt_account)
    elif accountType == 'DEMO': #模擬操作時
        # 顯示訊息
        print(datetime.fromtimestamp(int(datetime.now().timestamp())), accountType,'Account', order.action.upper(),optionDict[str(contract_txo.option_right)].upper(),contract_txo.symbol,'@',str(closePrice))
        # 發送telegram
        sendTelegram(accountType+' Account '+  order.action.upper()+' '+optionDict[str(contract_txo.option_right)].upper()+' '+contract_txo.symbol+'@'+str(closePrice), token, chatid)

    return

# 交易回報
def place_cb(stat, msg):
    global tradeRecord
    global openOrder
    global accountType
    global df_positions
    global SL
    global TP
    # global direction
    
    # 訂單回報
    if stat==sj.constant.OrderState.FOrder:
        print(datetime.fromtimestamp(int(datetime.now().timestamp())),'===下單回報===')
        optionRight='C' if str(msg['contract'].get('option_right'))=='OptionCall' else 'P'
        # optionRight='C' if str(msg['contract'].get('option_right'))=='OptionCall' else 'P'
        
        # 異常訂單
        # if msg['operation'].get('op_code')!='00':
        if msg.get('operation').get('op_code')!='00':
            print(datetime.fromtimestamp(int(datetime.now().timestamp())),msg['operation'].get('op_code'),msg['operation'].get('op_msg'))
            sendTelegram(msg['operation'].get('op_code')+msg['operation'].get('op_msg'), token, chatid)
        
            # 發送Telegram
        
        # 新訂單
        # if msg['operation'].get('op_type')=='New' and msg['operation'].get('op_code')=='00': 
        if msg.get('operation').get('op_type')=='New' and msg.get('operation').get('op_code')=='00': 
            print(datetime.fromtimestamp(int(datetime.now().timestamp())),'委託：','買入' if msg['order'].get('action')=='Buy' else '賣出' if msg['order'].get('action')=='Sell' else '無方向','價格:',str(msg['order'].get('price')),'數量：',str(msg['order'].get('quantity')),'代碼：',msg['contract'].get('code')+str(msg['contract'].get('delivery_month'))+str(int(msg['contract'].get('strike_price')))+optionRight)
            
            #顯示msg
            print(msg)
            
            # 發送Telegram
            
            # 紀錄新訂單
            openOrder.loc[datetime.fromtimestamp(int(msg['status']['exchange_ts'])),'ts']=datetime.fromtimestamp(int(msg['status']['exchange_ts']))
            openOrder.loc[openOrder.index[-1],'order_id']=msg.get('order').get('id')
            openOrder.loc[openOrder.index[-1],'order_seqno']=msg.get('order').get('seqno')
            openOrder.loc[openOrder.index[-1],'order_ordno']=msg.get('order').get('ordno')
            openOrder.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/openOrder.csv',mode='w',index=1)
             
        # 訂單更改
        
        # 取消訂單
        # if msg['operation'].get('op_type')!='Cancel':
        if msg.get('operation').get('op_type')=='Cancel':
            print(datetime.fromtimestamp(int(datetime.now().timestamp())),'訂單取消','買入' if msg['order'].get('action')=='Buy' else '賣出' if msg['order'].get('action')=='Sell' else '無方向','價格:',str(msg['order'].get('price')),'數量：',str(msg['order'].get('quantity')),'代碼：',msg['contract'].get('code')+str(msg['contract'].get('delivery_month'))+str(int(msg['contract'].get('strike_price')))+optionRight)
            
            #顯示msg
            print(msg)
            
            # 發送Telegram
            
            # 消除openOrder紀錄
            openOrder.drop(openOrder.index[-1],axis=0, inplace=True) 
            openOrder.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/openOrder.csv',mode='w',index=1)
        
    # 成交回報    
    if stat==sj.constant.OrderState.FDeal:
        print(datetime.fromtimestamp(int(datetime.now().timestamp())),'===成交回報===')
        optionRight='C' if str(msg['option_right'])=='OptionCall' else 'P'
        print(datetime.fromtimestamp(int(datetime.now().timestamp())),'訂單成交:','買入' if msg['action']=='Buy' else '賣出' if msg['action']=='Sell' else '','價格',msg['price'],'數量',msg['quantity'],'代碼：',msg['code']+msg['delivery_month']+str(int(msg['strike_price']))+optionRight)
        
        
        if msg['action']=='Buy':
            #顯示msg
            print(msg)
            
            # 更新交易紀錄：tradeRecord
            tradeRecord[datetime.fromtimestamp(int(msg['ts']))]={
                                                'Account Type':'LIVE',
                                                'Symbol':msg['code']+msg['delivery_month']+str(int(msg['strike_price']))+optionRight,
                                                'DateTime':datetime.fromtimestamp(int(msg['ts'])),
                                                'Entry Price':msg['price'],
                                                'Exit Price':0.,
                                                'Exit DateTime':'',
                                                'Quantity':msg['quantity'],
                                                'Unrealized PNL':0.,
                                                'Realized PNL':0.,
                                                'Commision':18*msg['quantity'],
                                                'Tax':math.ceil(msg['price']*50*0.001*msg['quantity']),
                                                'SL':SL,
                                                'TP':0.,
                                                }
        
            # 交易紀錄寫入CSV
            toCSV(tradeRecord,openTrade)
            
            # 列出期貨部位
            get_positions()
            if not df_positions.empty:
                tradeRecord[list(tradeRecord.keys())[-1]]['Unrealized PNL']
            
            # 按照3個id消除openOrder
            
        elif msg['action']=='Sell':
            #顯示msg
            print(msg)
            
            # 更新交易紀錄：tradeRecord
            tradeRecord[list(tradeRecord.keys())[-1]]['Exit Price']=msg['price']
            tradeRecord[list(tradeRecord.keys())[-1]]['Exit DateTime']=datetime.fromtimestamp(int(msg['ts']))
            tradeRecord[list(tradeRecord.keys())[-1]]['Commision']=tradeRecord[list(tradeRecord.keys())[-1]]['Commision']+18*msg['quantity']  #紀錄手續費
            tradeRecord[list(tradeRecord.keys())[-1]]['Tax']=tradeRecord[list(tradeRecord.keys())[-1]]['Tax']+math.ceil(msg['price']*50*0.001*msg['quantity'])  #紀錄稅
            tradeRecord[list(tradeRecord.keys())[-1]]['Realized PNL']=round(50*(msg['price']-tradeRecord[list(tradeRecord.keys())[-1]]['Entry Price']),0) #紀錄實現利潤
            tradeRecord[list(tradeRecord.keys())[-1]]['Unrealized PNL']=round(0.0,0) #未平倉損益歸零
  
            
            # 交易紀錄寫入CSV
            toCSV(tradeRecord,openTrade)
            
            # 列出期貨部位
            get_positions()
            
            # 按照3個id消除openOrder
       
    return

# 交易回報
api.set_order_callback(place_cb)

# 列出期貨部位
get_positions()
if not df_positions.empty:
    tradeRecord[list(tradeRecord.keys())[-1]]['Unrealized PNL']

@api.quote.on_event
def event_callback(resp_code: int, event_code: int, info: str, event: str):
    print(f'Event code: {event_code} | Event: {event}')
    return


def symbol2Contract(symbol):
    contract = api.Contracts.Options[symbol[:3]][symbol]
    return contract

# 將交易紀錄寫入csv
def toCSV(tradeRecord,openTrade):
    df_tradeRecord=pd.DataFrame.from_dict(tradeRecord,orient='index')
    df_tradeRecord.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/tradeRecord.csv',mode='w',index=0)
        
    df_openTrade=pd.DataFrame(openTrade)
    df_openTrade.to_csv('/Users/apple/Documents/code/PythonX86/ShioajiAPI/Output/openTrade.csv',mode='w',index=0)
        
    return

# 保持程式開啟
Event().wait()
