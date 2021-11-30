## 介紹
分析YouTube發佈的影片底下留言，將資料標記分為五大指標，針對`影片的喜愛`、 `YouTuber的喜愛`、`激動`、`諷刺`、`腥羶色`進行程度標記，針對五個標準的評分使用`FastText`模型進行訓練與預測。

每部影片的分析結果以網站和LINE Bot呈現，使用者只要輸入影片網址，就能即時爬蟲追蹤留言，進行YouTube影片的輿情分析，提供視覺化呈現，將非結構化訊息整理為有系統的資料。


## 網站架構流程
1. 爬蟲將資料寫入資料庫
2. 模型伺服器接受分析指令
3. 模型伺服器進行分析
4. 分析結果回傳資料庫
5. 回覆網頁伺服器請求結果
6. 網頁伺服器計算分析結果
7. 網站呈現 **歡迎到[網站](https://demo.jlwu.info:1108/youtubeai/)玩玩看！**

## 模型
- [模型訓練](https://github.com/tzuchyi/youtubeai/tree/main/model)

## 網站成果
- [website](https://demo.jlwu.info:1108/youtubeai/)

## 成果
- [成果報告](https://github.com/tzuchyi/youtubeai/blob/main/專題實作期末成果報告書0115.pdf)

