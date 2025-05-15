import colorama
import json
# --------------------------- Настройки ---------------------------
TOKEN = '8019616673:AAEUiUum3oh0GRmqaVXEvxRmqQwxouAMXAw'
debug = True
MAX_PLAYERS = 10
MIN_PLAYERS = 4


# ----------------- Переменные и функции системы ------------------
PATH = None
PATH_ME = __file__[:len(__file__) - len('config.py')]
DB_PATH = f'{PATH_ME}bot.db'
Chars_lson = f'{PATH_ME}chars.json'
with open(Chars_lson, 'r') as f:
    chars = dict(json.load(f))


def banner(text: str) -> str:
    '''
    Возращает текст в виде баннера
    '''
    out = ['', '', '', '', '']
    cnt = 0
    outStr = ''
    for char in text:
        cnt += len(chars[char][0])
        for line in range(0, 5):
            out[line] = f'{out[line]}{chars[char][line]}'
        if cnt >= 120:
            outStr += '\n'.join(out) + "\n"
            out = ['', '', '', '', '']
            cnt = 0
    outStr += '\n'.join(out)
    return outStr


def fprint(*pr, sep="", end="\n", type="STD", ret=False):
    '''
    :param pr: Несколько объектов для печати, будут склеяны через sep
    :param sep: Разделитель между объектами
    :param end: Окончание строки
    :param type: ЦВЕТА: С0 - белый, C1 - Красный, C2 - Синий, C3 - Зеленый, C4 - Желтый, C5 - Фиолетовый, C6 - Бирюзовый. 
    ФОРМАТ: T1 - Жирный, T2 - Подчеркнутый, T3 - Курсив, T4 - Зачеркнутый BANER - банер (Только английский)
    :param ret: При False - сразу печатает, при True возвращает кастомизированый текст
    '''
    text = sep.join(pr) + end
    Colors = colorama.Fore
    Style = colorama.Style
    reset = Style.RESET_ALL
    if type == "STD":
        if not ret:
            print(Colors.RESET + text, end='')
        else:
            return colorama.Fore.RESET + text
    else:
        collorText = ""
        F = type.split()
        for i in F:

            UnrightFormat = f"{Colors.RED} {Style.BRIGHT}    НЕПРАВИЛЬНЫЙ ФОРМАТ {Colors.RESET}"
            if len(i) == 2:
                if i[0] == "C":
                    if i[1] in list("0123456"):
                        Collor = int(i[1])
                        if Collor == 0:
                            collorText += Colors.RESET
                        elif Collor == 1:
                            collorText += Colors.RED
                        elif Collor == 2:
                            collorText += Colors.BLUE
                        elif Collor == 3:
                            collorText += Colors.GREEN
                        elif Collor == 4:
                            collorText += Colors.YELLOW
                        elif Collor == 5:
                            collorText += Colors.MAGENTA
                        elif Collor == 6:
                            collorText += Colors.CYAN
                    else:
                        print(UnrightFormat + "ЦВЕТ")
                elif i[0] == "T":
                    if i[1] in list("1234"):
                        Collor = int(i[1])
                        if Collor == 1:
                            collorText += Style.BRIGHT
                        elif Collor == 2:
                            collorText += '\033[4m'
                        elif Collor == 3:
                            collorText += '\033[3m'
                        elif Collor == 4:
                            collorText += '\033[9m'
                    else:
                        print(UnrightFormat + "ТИП")
                else:
                    print(UnrightFormat + "НЕ НАЙДЕН АРГУМЕНТ" + reset)
            elif i == "BANER":
                text = banner(text.upper())
            else:
                print(UnrightFormat + "НЕ НАЙДЕН АРГУМЕНТ" + reset)
        if not ret:
            print(collorText + text + reset, end="")
        else:
            return collorText + text + reset
