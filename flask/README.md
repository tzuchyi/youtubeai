## 呈現網站架設

### Author
Liu Hsuan, Kao Tzu-chyi

### 介紹
使用Flask編寫網站，串連資料庫將結果呈現在網站上。

本系統以 macOS 進行操作。

### 準備環境
* python
* [PyCharm](https://www.jetbrains.com/pycharm/download/#section=mac)

### 網站架構流程
1. 爬蟲將資料寫入資料庫
2. 模型伺服器接受分析指令
3. 模型伺服器進行分析
4. 分析結果回傳資料庫
5. 回覆網頁伺服器請求結果
6. 網頁伺服器計算分析結果
7. 網站呈現 
