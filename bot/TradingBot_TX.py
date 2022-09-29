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

[bugs]
收盤沒有收K線
開盤第一根K線怪怪的，似乎把盤前搓合的合併了。比對歷史K線看看

[未完工]
停損:半價
no higher high profit exit:
各個週期的賣訊作爲濾網：各週期都OK時長單，上級OK即短單。
在call-back函數之外再建立執行緒來計算
處理OrderState，Live從API回報了解庫存，未成交單子處理
選擇權的報價
加碼
觸價突破單
三重濾網
績效統計：勝率、賠率、破產率、平均獲利、平均損失、95%都在多少損失內
即時回測
tradingview來啟動 to IB&SinoPac API.
周選合約裡面找划算的
交易股票期貨

'''
import sys
import os
sys.path.append('/Users/apple/Documents/code/PythonX86')
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

# 讀取config
config = configparser.ConfigParser()
config.read('/Users/apple/Documents/code/PythonX86/Output/config.cfg')  # 讀入個人資料
PI = str(config.get('Login', 'PersonalId'))
PWD = str(config.get('Login', 'PassWord'))
CAPath = str(config.get('Login', 'CAPath'))
CAPWD = str(config.get('Login', 'CAPassWord'))
timeFrame1 = int(config.get('Trade', 'timeFrame1')) # 讀入交易設定：小週期K線週期
timeFrame2 = int(config.get('Trade', 'timeFrame2')) # 讀入交易設定：中週期K線週期
timeFrame3 = int(config.get('Trade', 'timeFrame3')) # 讀入交易設定：中週期K線週期
nDollar = int(config.get('Trade', 'nDollar'))   # 讀入交易設定：選擇權在多少錢以下

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

# 讀入telegram資料
config.read(
    '/Users/apple/Documents/code/Python/IB-native-API/Output/telegramConfig.cfg')
token = config.get('Section_A', 'token')
chatid = config.get('Section_A', 'chatid')

# 訂單設定
def readOrder():
    global direction
    global accountType
    global qty
    global orderCount
    # 讀入訂單設定檔
    df_order = pd.read_csv(
        '/Users/apple/Documents/code/PythonX86/Output/order.csv',index_col=False)
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
    global accountType0
    global direction0
    global qty0
    if (qty0!=qty) or (direction0!=direction) or (accountType0!=accountType):
        print('Setting:',accountType,'account',direction,qty)
        sendTelegram('Setting:'+accountType+' account '+direction+' '+str(qty), token, chatid)
        accountType0=accountType
        qty0=qty
        direction0=direction
    return

# 根據當前日期選擇近月合約：結算日則以次月合約
def selectFutures():
    year = datetime.now().year  # 今年
    month =datetime.now().month  # 這個月
    day=21-(dt.date(year,month,1).weekday()+4)%7         #   weekday函數 禮拜一為0;禮拜日為6
    
    if datetime.now().day>=day:     #計算下個月結算日
        month=month+1
        day=21-(dt.date(year,month,1).weekday()+4)%7 
   
    sym='TXF'+str(year)+str(month).zfill(2) #zfill(2)保持月份是兩位數
    print(sym,'Settlement date is',dt.date(year,month,day))
    contract=api.Contracts.Futures['TXF'][sym]
    return contract



# 從CSV讀入交易紀錄
def fromCSV():
    dict_tradeRecord={}
    list_openTrade=[]
    
    if not os.path.isfile('/Users/apple/Documents/code/PythonX86/Output/tradeRecord.csv'):
        # print({},[])
        return {},[]
    elif os.path.isfile('/Users/apple/Documents/code/PythonX86/Output/tradeRecord.csv') and not os.path.isfile('/Users/apple/Documents/code/PythonX86/Output/openTrade.csv'):
        df_tradeRecord=pd.read_csv('/Users/apple/Documents/code/PythonX86/Output/tradeRecord.csv',index_col=0)
        for index in df_tradeRecord.index:
            dict_tradeRecord[df_tradeRecord.loc[index,'DateTime']]=df_tradeRecord.loc[index].to_dict()
            # dict_tradeRecord.drop(index=dict_tradeRecord[dict_tradeRecord['Exit Price']==0].index,axis = 0,inplace = True)
        # print(dict_tradeRecord,[])
        return dict_tradeRecord,[]
    elif os.path.isfile('/Users/apple/Documents/code/PythonX86/Output/tradeRecord.csv') and os.path.isfile('/Users/apple/Documents/code/PythonX86/Output/openTrade.csv'):
        df_tradeRecord=pd.read_csv('/Users/apple/Documents/code/PythonX86/Output/tradeRecord.csv',index_col=0)
        for index in df_tradeRecord.index:
            dict_tradeRecord[df_tradeRecord.loc[index,'DateTime']]=df_tradeRecord.loc[index].to_dict()
            # dict_tradeRecord.drop(index=dict_tradeRecord[dict_tradeRecord['Exit Price']==0].index,axis = 0,inplace = True)
        try:
            df_openTrade=pd.read_csv('/Users/apple/Documents/code/PythonX86/Output/openTrade.csv')
            # df_openTrade=pd.read_csv('/Users/apple/Documents/code/PythonX86/Output/openTrade.csv',index=0)
        except:
            # print(dict_tradeRecord,[])
            return dict_tradeRecord,[]
        list_openTrade=df_openTrade.loc[0].to_list()
        # print(dict_tradeRecord,list_openTrade)
        return dict_tradeRecord,list_openTrade
    
# 檢查是否為休市期間
def ifOffMarket():
    # print('1',(datetime.now().strftime('%H:%M') >'05:00' and datetime.now().strftime('%H:%M') < '08:45'),'2',(datetime.now().strftime('%H:%M') > '13:45' and datetime.now().strftime('%H:%M') < '15:00'),'3',(datetime.now().isoweekday() in [6, 7]),'4',((datetime.now().strftime('%H:%M') >'05:00' and datetime.now().strftime('%H:%M') < '08:45') or (datetime.now().strftime('%H:%M') > '13:45' and datetime.now().strftime('%H:%M') < '15:00') or datetime.now().isoweekday() in [6, 7] ))
    return (datetime.now().strftime('%H:%M') >'05:00' and datetime.now().strftime('%H:%M') <= '08:45') or (datetime.now().strftime('%H:%M') > '13:45' and datetime.now().strftime('%H:%M') <='15:00') or datetime.now().isoweekday() in [6, 7] 
        
# 基本設定
# 呼叫策略函式
StrategyType = 'API'  # 告訴策略用API方式來處理訊號
st = Strategies(StrategyType)   # 策略函式
rm = RiskManage(StrategyType, 2)    # 風控函式

offMarket =ifOffMarket()   # 是否交易時間之外
placedOrder = 0  # 一開始下單次數為零
# 紀錄來與新的紀錄比對
accountType0=''
direction0=''
qty0=-1

# 中週期的方向初始值為無
direction2='None' 
direction3='None' 

#依照設定來動作
readOrder()
settingChange()
# 模擬賬戶紀錄
tradeRecord={}
openTrade=[]    #紀錄未平倉
# fromCSV(tradeRecord,openTrade)
# 合約設定
contract_txf = selectFutures()  # 選定期指合約
# 讀入過去交易紀錄
tradeRecord,openTrade=fromCSV()

# 歷史報價
api.quote.subscribe(contract_txf)  # 訂閱即時ticks資料
today=datetime.now().strftime('%F')
beforeYesterday=(datetime.now()-timedelta(days=1))
if beforeYesterday.isoweekday() ==7:
    beforeYesterday=(datetime.now()-timedelta(days=3)).strftime('%F')
else:
    beforeYesterday=(datetime.now()-timedelta(days=1)).strftime('%F')
kbars = api.kbars(contract_txf, start=beforeYesterday, end=today)  # 讀入歷史1分K
# kbars = api.kbars(contract_txf)  # 讀入歷史1分K
df0 = pd.DataFrame({**kbars})  # 先將Kbars物件轉換為Dict，再傳入DataFrame做轉換
df0.ts = pd.to_datetime(df0.ts)  # 將原本的ts欄位中的資料，轉換為DateTime格式並回存
df0.index = df0.ts  # 將ts資料，設定為DataFrame的index

# K線重組字典
resDict = {
    'Open': 'first',
    'High': 'max',
    'Low': 'min',
    'Close': 'last'
}

# 從合約讀取選擇權形式字典
optionDict = {'OptionRight.Call': 'Call', 'OptionRight.Put':'Put'}

# 重組1分線為小、中、大週期Ｋ線
# 小週期
df1 = df0.resample(str(timeFrame1)+'min', closed='left',label='left').agg(resDict)  
df1.reset_index(inplace=True)
# 中週期
df2 = df0.resample(str(timeFrame2)+'min', closed='left',label='left').agg(resDict)  
df2.reset_index(inplace=True)
# 大週期
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
df1.to_csv('/Users/apple/Documents/code/PythonX86/Output/df1.csv',index=1)
df2.to_csv('/Users/apple/Documents/code/PythonX86/Output/df2.csv',index=1)
df3.to_csv('/Users/apple/Documents/code/PythonX86/Output/df3.csv',index=1)

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
            if settleDict[m][w]>datetime.now().strftime("%F %H:%M:%S"): #比對哪個週結算日超過目前日期，此為最近的週結算日
                month=m
                weeks=w
                break   # 跳出所有迴圈
        else:
            continue
        break
    
    #計算履約價與合約價
    # contract_twi = api.Contracts.Indexs["001"]  # 大盤
    # snapshots_twi = api.snapshots([contract_twi])  # 取得大盤指數作為選取選擇權合約起點
    # print(df1.loc[df1.index[-1],'Close'],snapshots_twi[0].close)
    for count in range(1, 41):
        # 依照大盤轉換每50點間隔的履約價
        if direction.upper() == 'BUY':
            strikePrice = str(
                # int(snapshots_twi[0].close-snapshots_twi[0].close % 50+count*50))+'C'
                int(df1.loc[df1.index[-1],'Close']-df1.loc[df1.index[-1],'Close'] % 50+count*50))+'C'
        elif direction.upper() == 'SELL':
            strikePrice = str(
                # int(snapshots_twi[0].close-snapshots_twi[0].close % 50-(count-1)*50))+'P'
                int(df1.loc[df1.index[-1],'Close']-df1.loc[df1.index[-1],'Close'] % 50-(count-1)*50))+'P'
        
        tx = 'TX'+str(weeks) if weeks != 3 else 'TXO'  # 算出TX?
        sym=tx+str(year)+str(month).zfill(2)+strikePrice    # 算出當前日期適合的合約symbol
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),sym)
        try:
            contract=symbol2Contract(sym)
            snapshots = api.snapshots([contract])  # 取得合約的snapshots
            orderPrice = int(snapshots[0].close)  # 取得合約的價格
        
            print(datetime.fromtimestamp(int(datetime.now().timestamp())),sym, orderPrice)
            if orderPrice <= nDollar:  # 取得nDollar元以下最接近nDollar元的合約
                return contract
            tmpContract = contract
        except:
            pass
         
    contract = tmpContract  #如果沒有滿足nDollar以下的合約則以最接近的合約
    print(datetime.fromtimestamp(int(datetime.now().timestamp())),'tmpContract:', sym, price)

    return contract

# 接收tick報價
@api.quote.on_quote
def q(topic, quote):
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
    global openTrade
    global optionDict
    global direction2
    global direction3
    ts = pd.Timestamp(quote['Date']+' '+quote['Time'][:8])  # 讀入Timestamp
    close = quote['Close'][0] if isinstance(
        quote['Close'], list) else quote['Close']  # 放入tick值
    

    # 測試用
    # df1 = pd.DataFrame(data1,columns=['ts','Close'])
    # df1.ts = pd.to_datetime(df1.ts)
    # df1.index = df1.ts
    # df1.to_csv('/Users/apple/Documents/code/PythonX86/Output/df1.csv',index=0)
    
    
    
    
    # Timestamp在timeFrame1或timeFrame1的倍數時以及收盤時進行一次tick重組分K
    offMarket =ifOffMarket()   # 是否交易時間之外
    if not offMarket:
        data1.append([ts, close])
    # 判斷是否小週期收K線
    if (not offMarket and ts.minute/timeFrame1 == ts.minute//timeFrame1 and nextMinute1 != ts.minute and datetime.now().isoweekday() in [1,2,3,4,5]) or (datetime.now().strftime('%H:%M') in ['13:45', '05:00'] and nextMinute1 != ts.minute and datetime.now().isoweekday() in [1,2,3,4,5]):
        nextMinute1 = ts.minute  # 相同的minute1分鐘內只重組一次
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),
        #       'Market:Closed.' if offMarket else 'Market:Opened Bar Label:'+ts.strftime('%F %H:%M'))
        resampleBar(timeFrame1, data1)  # 重組K線
        
        
        unixtime = time.mktime(ts.timetuple())
        # print(unixtime/(timeFrame2*60),unixtime//(timeFrame2*60),datetime.now().timestamp(),unixtime,ts)

        # 進場訊號
        signal = st._RSI(df1)
        
        # 判斷是否中週期收K線
        # if (int(datetime.now().timestamp())/(timeFrame2*60) == int(datetime.now().timestamp())//(timeFrame2*60) and nextMinute2 != datetime.now().strftime('%H:%M')) or (datetime.now().strftime('%H:%M') in ['13:45','05:00'] and datetime.now().strftime('%H:%M')):
        # if (unixtime/(timeFrame2*60) == unixtime//(timeFrame2*60) and nextMinute2 != ts.strftime('%H:%M')) or (datetime.now().strftime('%H:%M') in ['13:45','05:00'] and nextMinute2 != ts.strftime('%H:%M')):
        if (ts.minute/timeFrame2 == ts.minute//timeFrame2 and nextMinute2 != ts.strftime('%H:%M')) or (datetime.now().strftime('%H:%M') in ['13:45','05:00'] and nextMinute2 != ts.strftime('%H:%M')):
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
            # df2.to_csv('/Users/apple/Documents/code/PythonX86/Output/df2.csv',index=1)
            
            print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Market:Closed.' if offMarket else 'Market:Opened',str(timeFrame2)+'K Bar:'+df2.index[-1].strftime('%F %H:%M'))


            ifActivateBot2=st._RSI_HTF(df2)
            if ifActivateBot2 =='BUY':  #進場訊號
                direction2='BUY'
                print(datetime.fromtimestamp(int(datetime.now().timestamp())),str(timeFrame2)+'m RSI low')
                sendTelegram(str(timeFrame2)+'m RSI low', token, chatid)
            elif ifActivateBot2 =='SELL':
                direction2='SELL'
                print(datetime.fromtimestamp(int(datetime.now().timestamp())),str(timeFrame2)+'m RSI high')
                sendTelegram(str(timeFrame2)+'m RSI high', token, chatid) 
                
            if (ts.minute/timeFrame3 == ts.minute//timeFrame3 and nextMinute3 != ts.strftime('%H:%M')):
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
                # df2.to_csv('/Users/apple/Documents/code/PythonX86/Output/df2.csv',index=1)
                print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Market:Closed.' if offMarket else 'Market:Opened',str(timeFrame3)+'K Bar:'+df3.index[-1].strftime('%F %H:%M'))

                ifActivateBot3=st._RSI_HTF(df3)
                if ifActivateBot3 =='BUY':  #進場訊號
                    direction3='BUY'
                    print(datetime.fromtimestamp(int(datetime.now().timestamp())),str(timeFrame3)+'m RSI low')
                    sendTelegram(str(timeFrame2)+'m RSI low', token, chatid)
                elif ifActivateBot3 =='SELL':
                    direction3='SELL'
                    print(datetime.fromtimestamp(int(datetime.now().timestamp())),str(timeFrame3)+'m RSI high')
                    sendTelegram(str(timeFrame3)+'m RSI high', token, chatid) 
            
            
        #依照設定更改動作
        readOrder()
        settingChange()
        
        
        # 停損（未完工）
        # if close<stopLossPrice:
    
        # 突破（未完工） 
        # if close>breakOutPrice:

        # 訊號處理
        if direction=='BUY':    #buy call
            if signal =='BUY' and direction2=='BUY' and direction3=='BUY':  #進場訊號 
                if len(openTrade)==0:
                    contract_txo = selectOption()   #選擇選擇權合約
                    snapshots = api.snapshots([contract_txo])  # 取得合約的snapshots
                    closePrice = snapshots[0].close #取得合約價格
                    order = selectOrder(signal,qty) #設定訂單
                    placeOrder(contract_txo, order) #下單
                    # 紀錄模擬交易紀錄
                    tradeRecord[ts.strftime('%F %H:%M:%S')]={'Symbol':contract_txo.symbol,
                                                         'DateTime':ts.strftime('%F %H:%M:%S'),
                                                         'Entry Price':closePrice,
                                                         'Exit Price':0.,
                                                         'Quantity':qty,
                                                         'Realized PNL':0.,
                                                         'Commision':18*qty,
                                                         'Tax':math.ceil(closePrice*50*0.001*qty),
                                                         'TP':0.,
                                                         'SL':5.
                                                         }
                    # 紀錄未平倉紀錄
                    openTrade.append(list(tradeRecord.keys())[-1])
                    # 寫入csv
                    toCSV(tradeRecord,openTrade)
                elif len(openTrade)!=0:     #如果未平倉不為零，留作未來加碼用
                    pass
            
            elif signal=='SELL':    #出場訊號 
                if len(openTrade)!=0:   #有部位
                    contract_txo = symbol2Contract(tradeRecord[openTrade[0]]['Symbol']) #讀取部位合約
                    snapshots = api.snapshots([contract_txo])  # 取得合約的snapshots
                    closePrice = snapshots[0].close #取得目前合約價
                    order = selectOrder(signal,tradeRecord[openTrade[0]]['Quantity'])   #設定平倉訂單
                    placeOrder(contract_txo, order) #下單
                    tradeRecord[openTrade[0]]['Exit Price']=closePrice  #紀錄出場價格
                    tradeRecord[openTrade[0]]['Commision']=tradeRecord[openTrade[0]]['Commision']+18*tradeRecord[openTrade[0]]['Quantity']  #紀錄手續費
                    tradeRecord[openTrade[0]]['Tax']=tradeRecord[openTrade[0]]['Tax']+math.ceil(closePrice*50*0.001*tradeRecord[openTrade[0]]['Quantity'])  #紀錄稅
                    tradeRecord[openTrade[0]]['Realized PNL']=round(50*(tradeRecord[openTrade[0]]['Exit Price']-tradeRecord[openTrade[0]]['Entry Price']),0) #紀錄利潤
                    openTrade=[]    #清空未平倉紀錄
                    toCSV(tradeRecord,openTrade)  #存入csv
                    # tradeRecord={}  # 清空交易紀錄
                    
        elif direction=='SELL':    #buy put
            if signal =='SELL' and direction2=='SELL' and direction3=='SELL':    # 設突破單（未完工） if close>breakOutPrice:
                if len(openTrade)==0:
                    contract_txo = selectOption()
                    snapshots = api.snapshots([contract_txo])  # 取得合約的snapshots
                    closePrice = snapshots[0].close
                    order = selectOrder('BUY',qty)
                    placeOrder(contract_txo, order)
                    tradeRecord[ts.strftime('%F %H:%M:%S')]={'Symbol':contract_txo.symbol,
                                                         'DateTime':ts.strftime('%F %H:%M:%S'),
                                                         'Entry Price':closePrice,
                                                         'Exit Price':0.,
                                                         'Quantity':qty,
                                                         'Realized PNL':0.,
                                                         'Commision':18*qty,
                                                         'Tax':math.ceil(closePrice*50*0.001*qty),
                                                         'TP':0.,
                                                         'SL':5.
                                                         }
                    openTrade.append(list(tradeRecord.keys())[-1])
                    toCSV(tradeRecord,openTrade)
                elif len(openTrade)!=0:
                    pass
                
            elif signal=='BUY': # 設停損單（未完工）if close<stopLossPrice:
                if len(openTrade)!=0:
                    contract_txo = symbol2Contract(tradeRecord[openTrade[0]]['Symbol'])
                    snapshots = api.snapshots([contract_txo])  # 取得合約的snapshots
                    closePrice = snapshots[0].close
                    order = selectOrder('SELL',tradeRecord[openTrade[0]]['Quantity'])
                    placeOrder(contract_txo, order)
                    tradeRecord[openTrade[0]]['Exit Price']=closePrice
                    tradeRecord[openTrade[0]]['Commision']=tradeRecord[openTrade[0]]['Commision']+18*tradeRecord[openTrade[0]]['Quantity']
                    tradeRecord[openTrade[0]]['Tax']=tradeRecord[openTrade[0]]['Tax']+math.ceil(closePrice*50*0.001*tradeRecord[openTrade[0]]['Quantity'])
                    tradeRecord[openTrade[0]]['Realized PNL']=round(50*(tradeRecord[openTrade[0]]['Exit Price']-tradeRecord[openTrade[0]]['Entry Price']),0)
                    
                    openTrade=[]
                    toCSV(tradeRecord,openTrade)   
                    # tradeRecord={}        

# 交易回報
# def place_cb(stat, msg):
#     print(datetime.fromtimestamp(int(datetime.now().timestamp())),
#           '__my_place_callback__')
#     print(datetime.fromtimestamp(int(datetime.now().timestamp())), stat, msg)
#     return

# 重組ticks轉換5分K
def resampleBar(period,data1):
    global df1
    global offMarket
    df_tick = pd.DataFrame(data1, columns=['ts', 'Close'])  #用來暫存ticks
    df_tick.ts = pd.to_datetime(df_tick.ts)
    df_tick.index = df_tick.ts
    # df_tick.to_csv('/Users/apple/Documents/code/PythonX86/Output/df_tick.csv',index=0)
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
    if len(df_res.ts) != 0: #當有新的重組K線時
        while df1.iloc[-1, 0] >= df_res.iloc[0, 0]:  #以新的重組K線的資料為主，刪除歷史K線最後幾筆資料
            df1.drop(df1.index[-1], axis=0, inplace=True)
    df1 = pd.concat([df1, df_res], ignore_index=True)  # 重組後分K加入原來歷史分K
    # print(df1)
    df1.reset_index(drop=True)   # 重置index保持連續避免dataframe操作錯誤
    df1.to_csv('/Users/apple/Documents/code/PythonX86/Output/df1.csv',index=1)
    # df_res.to_csv('/Users/apple/Documents/code/PythonX86/Output/df_res.csv',index=0)
    return
    
#設定訂單
def selectOrder(action,quantity):
    global contract_txo
    global optionDict
    global closePrice
    
    order = api.Order(
        action=action.title(),
        #  price=0.3, #價格
        # price=0,  # 價格
        price=closePrice-1,  # 價格
        quantity=quantity,  # 口數
         price_type='LMT',
        # price_type='MKP',
         order_type='ROD',
        # order_type='IOC',
        octype='Auto',  # 倉別，使用自動
        #  OptionRight='Call', #選擇權類型
        OptionRight=optionDict[str(contract_txo.option_right)],  # 選擇權類型
        account=api.futopt_account  # 下單帳戶指定期貨帳戶
    )
    return order

# 發送訂單
def placeOrder(contract_txo, order):
    global accountType
    global placedOrder
    global optionDict
    global orderCount
    if accountType == 'LIVE':   #實盤時
        if placedOrder <= orderCount:   #在未達限定操作次數時
            # 下單
            trade = api.place_order(contract_txo, order)
            # 顯示訊息
            print(datetime.fromtimestamp(int(datetime.now().timestamp())), accountType,'Account',  order.action.upper(),optionDict[str(contract_txo.option_right)],contract_txo.symbol,'@',str(closePrice))
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

def symbol2Contract(symbol):
    contract = api.Contracts.Options[symbol[:3]][symbol]
    return contract

# 將交易紀錄寫入csv
def toCSV(tradeRecord,openTrade):
    df_tradeRecord=pd.DataFrame.from_dict(tradeRecord,orient='index')
    df_tradeRecord.to_csv('/Users/apple/Documents/code/PythonX86/Output/tradeRecord.csv',mode='w',index=1)
        
    df_openTrade=pd.DataFrame(openTrade)
    df_openTrade.to_csv('/Users/apple/Documents/code/PythonX86/Output/openTrade.csv',mode='w',index=0)
        
    return

# 保持程式開啟
Event().wait()
