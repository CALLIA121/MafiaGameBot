import sqlite3 as sq
import os

from config import fprint, debug

DBlist = {1: 'Users', 2: 'Roles', 3: 'Games'}


def log(*t: str):
    if debug:
        text = ''
        for word in t:
            word = str(word)
            text = f'{text} {word}'

        fprint('LOG:', type='C6', end='')
        fprint(text)


def succes(*t: str):
    if debug:
        text = ''
        for word in t:
            word = str(word)
            text = f'{text} {word}'

        fprint('SUCCES: ', type='C3', end='')
        fprint(text)


def connectTo(file_path: str) -> bool:
    """
    Подключается к базе данных.
    :param file_path: путь к базе
    :return: Удалось ли подключиться
    """
    fprint("Try connect to ", end='')
    fprint(file_path, type='T2')
    global connect
    global cursor
    if not os.path.exists(file_path):
        return False
    try:
        connect = sq.connect(file_path, check_same_thread=False)
        cursor = connect.cursor()
        return True
    except Exception:
        return False


def DeleteData(DB: int,
               qvest=None
               ) -> None:
    '''
    Удаление данных из базы.
    :param DB: {1: 'Users', 2:'Roles', 3:'Games'}
    :param qvest: условия для удаления, при передаче числа будет распознано как id, иначе пишите !<Sq3 условие>.
    '''
    global connect
    global cursor

    if qvest is None:
        log(f'DELETE FROM {DBlist[DB]}')
        cursor.execute(f'DELETE FROM {DBlist[DB]}')
        connect.commit()
        return None

    isID = True
    if isinstance(qvest, str):
        if qvest[0] == "!":
            isID = False

    if isID:
        qvest = f'ID = {qvest}'
    else:
        qvest = qvest[1:]

    log(f'DELETE FROM {DBlist[DB]} WHERE {qvest}')
    cursor.execute(f'DELETE FROM {DBlist[DB]} WHERE {qvest}')
    connect.commit()
    succes()


def writeData(DB: int,
              st: tuple,
              value: tuple,
              qvest=None
              ) -> None:
    '''
    Запись данных в базу.
    :param st: столбцы для записи.
    :param DB: {1: 'Users', 2:'Roles', 3:'Games'}.
    :param qvest: условия для записи, при передаче числа будет распознано как id, иначе пишите !<Sq3 условие>.
    :param value: данные для записи.
    '''
    global connect
    global cursor
    try:

        if isinstance(st, str):
            log('Transform', st, '->', '(`' + st + '`)')
            st = '(`' + st + '`)'

        if isinstance(value, list):
            if isinstance(value[0], tuple):
                valueR = value
                value = f"{', '.join((map(str, value)))}"

                log('Transform', valueR, '->', value)
            elif isinstance(value[0], str):
                valueR = value
                value = f"""('{ "'), ('".join((map(str, value)))}')"""

                log('Transform', valueR, '->', value)
            else:
                valueR = value
                value = f"""({'), ('.join((map(str, value)))})"""

                log('Transform', valueR, '->', value)
        elif isinstance(value, tuple):
            pass
        else:
            log('Transform', value, '->', f"""("{value}")""")
            value = f"""('{value}')"""

        if qvest is None:
            log(f'\n INSERT INTO {DBlist[DB]} {st} VALUES {value}')
            cursor.execute(
                f'INSERT INTO {DBlist[DB]} {st} VALUES {value}')
            connect.commit()
            fprint('SUCCES', type='C3')
            return

        isID = True
        if isinstance(qvest, str):
            if qvest[0] == "!":
                isID = False

        if isID:
            qvest = f'`ID` = "{qvest}"'
        else:
            qvest = qvest[1:]

        log(f'\n UPDATE `{DBlist[DB]}` SET {st} = {value} WHERE {qvest}')
        cursor.execute(
            f'''UPDATE `{DBlist[DB]}` SET {st} = {value} WHERE {qvest}''')
        succes()

        connect.commit()
    except Exception as e:
        fprint('ERROR INSERT: ', type='C1', end='')
        fprint(e)


def getData(DB: int,
            st: str,
            qvest="!1 = 1",
            All=False) -> list:
    '''
    :param st: столбец для чтения.
    :param DB: {1: 'Users', 2:'Roles', 3:'Games'}.
    :param qvest: условия для чтения, при передаче числа будет распознано как id, иначе пишите !<Sq3 условие>.
    :param All: Выбрать все, или только одну запись
    '''
    global connect
    global cursor

    DB = DBlist[DB]

    try:

        if isinstance(st, str):
            log('Transform', st, '->', '(`' + st + '`)')
            st = '(`' + st + '`)'
        elif isinstance(st, tuple):
            log('Transform', st, '->', ', '.join(st))
            st = ', '.join(st)

        isID = True
        if isinstance(qvest, str):
            if qvest[0] == "!":
                isID = False

        if isID:
            qvest = f"`ID` = {qvest}"
        else:
            qvest = qvest[1:]

        log(f'''SELECT {st} FROM `{DB}` WHERE {qvest}''')
        cursor.execute(f'''SELECT {st} FROM `{DB}` WHERE {qvest}''')
        result = cursor.fetchall()

        if All:
            if result is None:
                ret = []
            else:
                buff = []
                for line in result:
                    if ',' in st or '*' in st:
                        buff.append(tuple(line))
                    else:
                        buff.append(line[0])

                ret = buff
        else:
            if result is None:
                ret = None
            else:
                if ',' in st or '*' in st:
                    ret = tuple(result[0])
                else:
                    ret = result[0][0]

        succes(ret)
        return ret

    except Exception as e:
        fprint('ERROR SELECT: ', type='C1', end='')
        fprint(e)


def check(TGID):
    cursor.execute(f'''SELECT * FROM `{DBlist[1]}` WHERE `ID` = {TGID}''')
    result = cursor.fetchone()
    return False if result is None else True
