Gets to 99% accuracy every time with the 200 vectors dataset:
`python .\main.py model --dt-values=finishes,locals,wins,score,rank --dataset .\dataset.csv --epochs 80 --batch-size 40 --out model_speed_improved.h5 --inner-laye
rs 100:sigmoid 100:sigmoid 100:sigmoid`