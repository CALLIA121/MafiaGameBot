import sqlite3 as sq
import os

from config import fprint, debug

DBlist = {1: 'Users', 2: 'Rols', 3: 'Games'}

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


def writeData(DB: int,
              st: str,
              value,
              qvest=None
              ) -> None:
    '''
    Запись данных в базу.
    :param st: столбец для записи.
    :param DB: {1: 'Users', 2: 'Rols', 3: 'Games'}.
    :param qvest: условия для записи, при передаче числа будет распознано как id, иначе пишите !<Sq3 условие>.
    :param value: данные для записи.
    '''
    global connect
    global cursor
    global debug

    if qvest is None:
        if debug:
            print(f'INSERT INTO {DBlist[DB]} ({st}) VALUES {value}')
        cursor.execute(
            f'INSERT INTO {DBlist[DB]} ({st}) VALUES {value}')
        connect.commit()
        return None

    isID = True
    if isinstance(qvest, str):
        if qvest[0] == "!":
            isID = False

    if isID:
        qvest = int(qvest)
        cursor.execute(
            f'''SELECT ID FROM `{DBlist[DB]}` WHERE `ID` = {qvest}''')
        result = cursor.fetchone()
        if debug:
            print(
                f'''SELECT ID FROM `{DBlist[DB]}` WHERE `ID` = {qvest} ->''', result)
        if result is None:
            if debug:
                print(
                    f'INSERT INTO `{DBlist[DB]}` ({st}, ) VALUES {value}')
            cursor.execute(
                f'INSERT INTO `{DBlist[DB]}` ({st}) VALUES {value}')
        else:
            cursor.execute(
                f'''UPDATE `{DBlist[DB]}` SET ({st}) = ({value}) WHERE `ID` = {qvest}''')
    else:
        qvest = qvest[1:]
        cursor.execute(f'''SELECT `{st}` FROM `{DBlist[DB]}` WHERE {qvest}''')
        result = cursor.fetchone()
        if result is None:
            cursor.execute(
                f'INSERT INTO `{DBlist[DB]}` ({st}) VALUES {value}')
        else:
            cursor.execute(
                f'''UPDATE `{DBlist[DB]}` SET `{st}` = {value} WHERE {qvest}''')
    connect.commit()


def getData(DB: int,
            st: str,
            qvest="!1 = 1") -> list:
    '''
    :param st: столбец для чтения.
    :param DB: {1: 'Users', 2: 'Rols', 3: 'Games'}.
    :param qvest: условия для чтения, при передаче числа будет распознано как id, иначе пишите !<Sq3 условие>.
    '''
    global connect
    global cursor
    global debug

    DB = DBlist[DB]

    isID = True
    if isinstance(qvest, str):
        if qvest[0] == "!":
            isID = False

    if isID:
        qvest = int(qvest)
        if debug:
            print(f'''SELECT {st} FROM `{DB}` WHERE `ID` = {qvest}''')
        cursor.execute(f'''SELECT {st} FROM `{DB}` WHERE `ID` = {qvest}''')
        result = cursor.fetchall()
        if result is None:
            return []
        else:
            buff = []
            for line in result:
                if ',' in st or '*' in st:
                    buff.append(tuple(line))
                else:
                    buff.append(line[0])

            return buff
    else:
        qvest = qvest[1:]
        cursor.execute(f'''SELECT {st} FROM `{DB}` WHERE {qvest}''')
        result = cursor.fetchall()
        if result is None:
            return []
        else:
            buff = []
            for line in result:
                if ',' in st or '*' in st:
                    buff.append(tuple(line))
                else:
                    buff.append(line[0])

            return buff


def check(TGID):
    cursor.execute(f'''SELECT * FROM `{DBlist[1]}` WHERE `ID` = {TGID}''')
    result = cursor.fetchone()
    return False if result is None else True


def getTabls(DB):
    cursor.execute(f'''SELECT * FROM `{DBlist[DB]}`''')
    result = cursor.fetchone()
    return cursor.description


def getAll(DB):
    cursor.execute(f'''SELECT * FROM `{DBlist[DB]}`''')
    result = cursor.fetchall()
    return result


def DeleteData(DB: int,
               qvest=None
               ) -> None:
    '''
    Удаление данных из базы.
    :param DB: {1: 'Users', 2: 'Rols', 3: 'Games'}.
    :param qvest: условия для удаления, при передаче числа будет распознано как id, иначе пишите !<Sq3 условие>.
    '''
    global connect
    global cursor
    global debug

    if qvest is None:
        if debug:
            print(f'DELETE FROM {DBlist[DB]}')
        cursor.execute(f'DELETE FROM {DBlist[DB]}')
        connect.commit()
        return None

    isID = True
    if isinstance(qvest, str):
        if qvest[0] == "!":
            isID = False

    if isID:
        qvest = int(qvest)
        if debug:
            print(f'DELETE FROM {DBlist[DB]} WHERE ID = {qvest}')
        cursor.execute(f'DELETE FROM {DBlist[DB]} WHERE ID = {qvest}')
    else:
        qvest = qvest[1:]
        if debug:
            print(f'DELETE FROM {DBlist[DB]} WHERE {qvest}')
        cursor.execute(f'DELETE FROM {DBlist[DB]} WHERE {qvest}')

    connect.commit()
