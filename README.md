# Python Based Tooltip Dictionary

파이썬 기반의 툴팁 사전입니다. 기본적으로 SumatraPDF에서 사용하도록 설정되어 있습니다.

This is a python 3 based tooltip dictionary. Basically this works with SumatraPDF.

## 사용법

1. 필요한 패키지들을 아래와 같이 설치합니다.

```
pip install -r requirements.txt
```

2. <code>tooltip-dict.py</code> 파일의 가장 위에 있는 <code>app_list</code> 안에 원하는 프로그램의 exe명을 추가하세요.
3. <code>tooltip-dict.py</code> 파일 안의 <code>make_tooltip()</code> 함수를 원하시는 사전에 맞게 수정해야 합니다. 예시 코드가 적혀있습니다.

## How to Use

1. Install required packages.

```
pip install -r requirements.txt
```

2. Append the programs' exe file name you want to use to <code>app_list</code> at the top of <code>tooltip-dict.py</code>.
3. Edit <code>make_tooltip()</code> function in <code>tooltip-dict.py</code> to use the dictionary you want like the example.
