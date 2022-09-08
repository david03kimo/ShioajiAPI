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

[未完工]
處理OrderState
Live從API回報了解庫存
未成交單子處理
停損:半價
交易紀錄存在CSV可以延續不因程式中斷而重新計算
在call-back函數之外再建立執行緒來計算
觸價突破單
加碼
選擇權的訊號:同時要求許多連線，多週期：三重濾網
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
period = int(config.get('Trade', 'period'))
nDollar = int(config.get('Trade', 'nDollar'))

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
    df_order = pd.read_csv(
        '/Users/apple/Documents/code/PythonX86/Output/order.csv',index_col=False)
    df_order = df_order.values.tolist()
    a = df_order[0][0].split()
    orderCount=int(a[0])    #下單的次數限制
    
    direction = a[1].upper()    #操作的方向：多、空
    if direction not in ['BUY', 'SELL']:
        print('Wrong Action!!!')
        c = input('___________________')

    qty = int(a[2]) #下單的數量
    if qty == 0:
        accountType = 'DEMO'    #模擬操作
        qty = 1
    else:
        accountType = 'LIVE'    #實盤操作

    return

# 發送訊息到Telegram
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

# 選定選擇權合約
def selectOption():
    '''
    需要把所有大盤上下10檔都snapshop出報價來選擇一定價格以下的合約
    '''
    global orderPrice
    
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
    contract_twi = api.Contracts.Indexs["001"]  # 大盤
    snapshots_twi = api.snapshots([contract_twi])  # 取得大盤指數作為選取選擇權合約起點
    for count in range(1, 41):
        # 依照大盤轉換每50點間隔的履約價
        if direction.upper() == 'BUY':
            strikePrice = str(
                int(snapshots_twi[0].close-snapshots_twi[0].close % 50+count*50))+'C'
        elif direction.upper() == 'SELL':
            strikePrice = str(
                int(snapshots_twi[0].close-snapshots_twi[0].close % 50-(count-1)*50))+'P'
        
        tx = 'TX'+str(weeks) if weeks != 3 else 'TXO'  # 算出TX?
        sym=tx+str(year)+str(month).zfill(2)+strikePrice    # 算出當前日期適合的合約symbol
        print(datetime.fromtimestamp(int(datetime.now().timestamp())),sym)

        try:
            # contract = api.Contracts.Options[tx][sym]  # 取得合約
            contract=symbol2Contract(sym)
            snapshots = api.snapshots([contract])  # 取得合約的snapshots
            orderPrice = int(snapshots[0].close)  # 取得合約的價格
            # print(datetime.fromtimestamp(int(datetime.now().timestamp())),sym, price)
            if orderPrice <= nDollar:  # 取得nDollar元以下最接近nDollar元的合約
                return contract
            tmpContract = contract
        except:
            pass
         
    contract = tmpContract  #如果沒有滿足nDollar以下的合約則以最接近的合約
    print(datetime.fromtimestamp(int(datetime.now().timestamp())),'tmpContract:', sym, price)

    return contract

# 尚未完成
# def fromCSV(tradeRecord,openTrade):
#     if not os.path.isfile('/Users/apple/Documents/code/PythonX86/Output/tradeRecord.csv'):
#         pass
#     else: 
        
#         a=pd.read_csv('/Users/apple/Documents/code/PythonX86/Output/tradeRecord.csv')
#         # print(a.iloc[-1,1])
        
#         # input('xxx')
#         tradeRecord[a.iloc[-1,1]]=a
#         # openTrade.append[a.iloc[-1,1]]
#         openTrade.append(list(tradeRecord.keys())[-1])
#         # print(tradeRecord)
#         # print(openTrade)
#         # c=input('xxxxx')

        
#         with open('/Users/apple/Documents/code/PythonX86/Output/tradeRecord.csv',"r") as fin:
#              with open('/Users/apple/Documents/code/PythonX86/Output/tradeRecord.csv',"w") as fout:
#                 writer=csv.writer(fout)
#                 for row in csv.reader(fin):
#                     writer.writerow(row[:-1])
#     return

# 基本設定
# 呼叫策略函式
StrategyType = 'API'  # 告訴策略用API方式來處理訊號
st = Strategies(StrategyType)   # 策略函式
rm = RiskManage(StrategyType, 2)    # 風控函式

nowTime = datetime.now().strftime('%H:%M')
offMarket = (nowTime >='05:00' and nowTime < '08:45') or (nowTime >= '13:45' and nowTime < '15:00') or datetime.now().isoweekday() in [6, 7]   # 交易時間之外
print(datetime.fromtimestamp(int(datetime.now().timestamp())),
      'Shioaji API start!', 'Market Closed' if offMarket else 'Market Opened')
placedOrder = 0  # 一開始下單次數為零
# 紀錄來與新的紀錄比對
accountType0=''
direction0=''
qty0=-1
#依照設定來動作
readOrder()
settingChange()
# 模擬賬戶紀錄
tradeRecord={}
openTrade=[]    #紀錄未平倉
# fromCSV(tradeRecord,openTrade)
# 合約設定
contract_txf = selectFutures()  # 選定期指合約

# 歷史報價
api.quote.subscribe(contract_txf)  # 訂閱即時ticks資料
kbars = api.kbars(contract_txf)  # 讀入歷史1分K
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
df = df0.resample(str(period)+'min', closed='left',label='left').agg(resDict)  # 將1分K重組成5分K
NextMinute = int(datetime.now().minute)  # 紀錄最新一筆分K的分鐘數進行比對
print(datetime.fromtimestamp(int(datetime.now().timestamp())),
      'Market Closed.' if offMarket else 'Market Opened.K Bar label:'+str(NextMinute-NextMinute % period))  # 顯示分K的開始分鐘數
df.reset_index(inplace=True)
# df.to_csv('/Users/apple/Documents/code/PythonX86/Output/df.csv',index=0)

data1 = []
df.dropna(axis=0, how='any', inplace=True)  # 去掉交易時間外的空行
# df.to_csv('/Users/apple/Documents/code/PythonX86/Output/df.csv',index=0)


# 接收tick報價
@api.quote.on_quote
def q(topic, quote):
    global NextMinute
    global df
    global data1
    global closePrice
    global contract_txo
    global tradeRecord
    global period
    global openTrade
    global optionDict
    ts = pd.Timestamp(quote['Date']+' '+quote['Time'][:8])  # 讀入Timestamp
    close = quote['Close'][0] if isinstance(
        quote['Close'], list) else quote['Close']  # 放入tick值
    data1.append([ts, close])

    # 測試用
    # df1 = pd.DataFrame(data1,columns=['ts','Close'])
    # df1.ts = pd.to_datetime(df1.ts)
    # df1.index = df1.ts
    # df1.to_csv('/Users/apple/Documents/code/PythonX86/Output/df1.csv',index=0)
    
    # Timestamp在period或period的倍數時以及收盤時進行一次tick重組分K
    if ts.minute/period == ts.minute//period and NextMinute != ts.minute or datetime.now().strftime('%H:%M') in ['13:45', '05:00'] and not offMarket:
        NextMinute = ts.minute  # 相同的minute1分鐘內只重組一次
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),
        #       'Market:Closed.' if offMarket else 'Market:Opened Bar Label:'+ts.strftime('%F %H:%M'))
        resampleBar(period, data1)  # 重組K線

        # 進場訊號
        signal = st._RSI(df)
        #依照設定更改動作
        readOrder()
        settingChange()

        # 訊號處理
        if direction=='BUY':    #buy call
            if signal =='BUY':  #進場訊號
                if len(openTrade)==0:
                    contract_txo = selectOption()   #選擇選擇權合約
                    snapshots = api.snapshots([contract_txo])  # 取得合約的snapshots
                    closePrice = snapshots[0].close #取得合約價格
                    order = selectOrder(signal,qty) #設定訂單
                    placeOrder(contract_txo, order) #下單
                    # 紀錄模擬交易紀錄
                    tradeRecord[ts.strftime('%F %H:%M')]={'Symbol':contract_txo.symbol,
                                                         'DateTime':ts.strftime('%F %H:%M'),
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
                    toCSV(tradeRecord)
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
                    tradeRecord[openTrade[0]]['Realized PNL']=50*(tradeRecord[openTrade[0]]['Exit Price']-tradeRecord[openTrade[0]]['Entry Price']) #紀錄利潤
                    openTrade=[]    #清空未平倉紀錄
                    toCSV(tradeRecord)  #存入csv
                    tradeRecord={}  # 清空交易紀錄
                    
        elif direction=='SELL':    #buy put
            if signal =='SELL':
                if len(openTrade)==0:
                    contract_txo = selectOption()
                    snapshots = api.snapshots([contract_txo])  # 取得合約的snapshots
                    closePrice = snapshots[0].close
                    order = selectOrder('BUY',qty)
                    placeOrder(contract_txo, order)
                    tradeRecord[ts.strftime('%F %H:%M')]={'Symbol':contract_txo.symbol,
                                                         'DateTime':ts.strftime('%F %H:%M'),
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
                    toCSV(tradeRecord)
                elif len(openTrade)!=0:
                    pass
                
            elif signal=='BUY':
                if len(openTrade)!=0:
                    contract_txo = symbol2Contract(tradeRecord[openTrade[0]]['Symbol'])
                    snapshots = api.snapshots([contract_txo])  # 取得合約的snapshots
                    closePrice = snapshots[0].close
                    order = selectOrder('SELL',tradeRecord[openTrade[0]]['Quantity'])
                    placeOrder(contract_txo, order)
                    tradeRecord[openTrade[0]]['Exit Price']=closePrice
                    tradeRecord[openTrade[0]]['Commision']=tradeRecord[openTrade[0]]['Commision']+18*tradeRecord[openTrade[0]]['Quantity']
                    tradeRecord[openTrade[0]]['Tax']=tradeRecord[openTrade[0]]['Tax']+math.ceil(closePrice*50*0.001*tradeRecord[openTrade[0]]['Quantity'])
                    tradeRecord[openTrade[0]]['Realized PNL']=50*(tradeRecord[openTrade[0]]['Exit Price']-tradeRecord[openTrade[0]]['Entry Price'])
                    
                    openTrade=[]
                    toCSV(tradeRecord)    
                    tradeRecord={}        

    # 設停損單（未完工）
    # if close<stopLossPrice:

    # 設突破單（未完工）
    # if close>breakOutPrice:


# 交易回報
def place_cb(stat, msg):
    print(datetime.fromtimestamp(int(datetime.now().timestamp())),
          '__my_place_callback__')
    print(datetime.fromtimestamp(int(datetime.now().timestamp())), stat, msg)
    return

# 重組ticks轉換5分K
def resampleBar(period, data1):
    global df
    df1 = pd.DataFrame(data1, columns=['ts', 'Close'])  #用來暫存ticks
    df1.ts = pd.to_datetime(df1.ts)
    df1.index = df1.ts
    # df1.to_csv('/Users/apple/Documents/code/PythonX86/Output/df1.csv',index=0)
    df_res = df1.Close.resample(
        str(period)+'min', closed='left', label='left').agg(resDict)  # tick重組分K
    del data1[0:len(data1)-1]  # 只保留最新的一筆tick，減少記憶體佔用
    df_res.drop(df_res.index[-1], axis=0, inplace=True)  # 去掉最新的一筆分K，減少記憶體佔用
    print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Market:Closed.' if offMarket else 'Market:Opened Bar Label:'+df_res.index[-1].strftime('%F %H:%M'))
    df_res.reset_index(inplace=True)
    df_res.dropna(axis=0, how='any', inplace=True)  # 去掉空行
    if len(df_res.ts) != 0: #當有新的重組K線時
        while df.iloc[-1, 0] >= df_res.iloc[0, 0]:  #以新的重組K線的資料為主，刪除歷史K線最後幾筆資料
            df.drop(df.index[-1], axis=0, inplace=True)
    df = pd.concat([df, df_res], ignore_index=True)  # 重組後分K加入原來歷史分K
    # df.to_csv('/Users/apple/Documents/code/PythonX86/Output/df.csv',index=0)
    # df_res.to_csv('/Users/apple/Documents/code/PythonX86/Output/df_res.csv',index=0)
    return
    
#設定訂單
def selectOrder(action,quantity):
    global contract_txo
    global optionDict
    global orderPrice
    
    order = api.Order(
        action=action.title(),
        #  price=0.3, #價格
        # price=0,  # 價格
        price=orderPrice-1,  # 價格
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

# 將交易紀錄寫入csv(未完工)
def toCSV(tradeRecord):
    a=[]
    for i in tradeRecord.keys():
        a.append(tradeRecord[i])
    df_tradeRecord=pd.DataFrame(a)
    if not os.path.isfile('/Users/apple/Documents/code/PythonX86/Output/tradeRecord.csv'):
        df_tradeRecord.to_csv('/Users/apple/Documents/code/PythonX86/Output/tradeRecord.csv',sep=',',mode='w',index=True,header=True)
    elif df_tradeRecord.iloc[-1,5]==0: 
        with open('/Users/apple/Documents/code/PythonX86/Output/tradeRecord.csv',"r") as fin:
             with open('/Users/apple/Documents/code/PythonX86/Output/tradeRecord.csv',"w") as fout:
                writer=csv.writer(fout)
                for row in csv.reader(fin):
                    writer.writerow(row[:-1])
                    #  and df_tradeRecord.[-1,1]==
        df_tradeRecord.to_csv('/Users/apple/Documents/code/PythonX86/Output/tradeRecord.csv',sep=',', index=True,mode='a', header=False)
    else:
        df_tradeRecord.to_csv('/Users/apple/Documents/code/PythonX86/Output/tradeRecord.csv',sep=',', index=True,mode='a', header=False)

    return

# 保持程式開啟
Event().wait()
