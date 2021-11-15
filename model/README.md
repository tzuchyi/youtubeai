## 模型訓練

### Author
Chou Hsin-te, Hsu Ching-wen

### 介紹
我們參考GitHub裡面的7組模型，去進行改寫，選擇符合我們需求的模型。
1. FastText
2. TextCNN
3. TextRNN
4. TextRNN_Att
5. TextRCNN
6. DPCNN
7. Transformers

### 準備環境
* python 3.7
* pytorch 1.1
* tqdm
* sklearn
* tensorboardX
### 使用說明
1.將訓練集、測試集、驗證集及分類名稱，放入THUCNews/Data資料夾
2.在終端機到指定路徑
3.如果用詞，提前分好詞，詞之間用空格隔開，輸入python run.py --model FastText --word True
4.預測結果將以ckpt檔形式存取在THUCNews/saved_dict
### 參考資料
[Chinese-Text-Classification-Pytorch](https://github.com/649453932/Chinese-Text-Classification-Pytorch)
