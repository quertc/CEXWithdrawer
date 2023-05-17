import time
import random
import os
import csv
from sys import stderr

import ccxt
import inquirer
from termcolor import colored
from loguru import logger
from art import text2art

from modules.cipher import PasswordEncryption


wallets_file = 'files/wallets.csv'
api_keys_file = 'files/encrypted_keys.txt'
log_file = 'logs/log.log'
proxy_file = 'files/proxy.txt'


logger.remove()
logger.add(stderr, format="<white>{time:HH:mm:ss}</white> | <level>{level: <8}</level> | <cyan>{line}</cyan> - <white>{message}</white>")
logger.add(log_file, format="<white>{time:HH:mm:ss}</white> | <level>{level: <8}</level> | <cyan>{line}</cyan> - <white>{message}</white>")


class Exchange:

    def __init__(self, name: str, api_key: str, api_secret: str, password: str) -> None:
        self.name = name
        self.exchange = getattr(ccxt, self.name)({
            'apiKey': api_key,
            'secret': api_secret,
            'password': password,
            'enableRateLimit': True,
            'proxies': get_proxy() if self.name == 'okx' else None,
            'options': {
                'defaultType': 'spot'
            }
        })


    def get_withdraw_chains(self, symbol: str) -> list:
        chains = [] 
        try:
            coin_data = self.exchange.fetch_currencies()[symbol]
            if self.name == 'binance':
                for chain in coin_data['networks']:
                    if chain['withdrawEnable'] == True:
                        network_name = chain['network']
                        withdraw_fee = float(chain['withdrawFee'])
                        withdraw_min = float(chain['withdrawMin'])
                        chains.append([network_name, withdraw_fee, withdraw_min])
            else:
                for chain in coin_data['networks'].values():
                    if chain['withdraw'] == True:
                        network_name = chain['network']
                        withdraw_fee = float(chain['fee'])
                        withdraw_min = float(chain['limits']['withdraw']['min'])
                        chains.append([network_name, withdraw_fee, withdraw_min])
            return chains
        except KeyError as e:
            print(colored(f"Такого символа нет на бирже! Попробуйте ввести снова.", 'light_red'))
            return False
        except Exception as e:
            if 'Invalid API-key' in str(e) or 'Unmatched IP' in str(e):
                print(colored(f"Ошибка: Скорее всего, ваш текущий IP адрес не находится в белом списке на вывод средств или API-ключ истек!", 'light_red'))
            elif 'GET' in str(e):
                print(colored(f"Ошибка: Биржа временно недоступна, либо недоступна в вашей локации, либо ваш прокси нерабочий.", 'light_red'))
            else:
                print(colored(f"Неизвестная ошибка получения доступных сетей вывода: {e}", 'light_red'))
            return False


    def withdraw(self, address: str, amount_to_withdrawal: float, symbol_to_withdraw: str, network: str, withdraw_fee: float) -> None:
        try:
            if self.name == 'okx':
                self.exchange.withdraw(
                    code=symbol_to_withdraw,
                    amount=amount_to_withdrawal,
                    address=address,
                    tag=None, 
                    params={
                        "toAddress": address,
                        "chain": f"{symbol_to_withdraw}-{network}",
                        "dest": 4,
                        "fee": withdraw_fee,
                        "pwd": '-',
                        "amt": amount_to_withdrawal,
                    }
                )
            else:
                self.exchange.withdraw(
                    code=symbol_to_withdraw,
                    amount=amount_to_withdrawal,
                    address=address,
                    tag=None, 
                    params={
                        "network": network
                    }
                )
            logger.success(colored(f"{address} | Успешно выведено {amount_to_withdrawal} {symbol_to_withdraw}", 'green', attrs=['bold', 'blink']))
            return True
        except ccxt.InsufficientFunds as e:
            logger.error(colored(f'{address} | Ошибка: Недостаточно средств на балансе!', 'light_red'))
            return False
        except ccxt.ExchangeError as e:
            if 'not equal' in str(e) or 'not whitelisted' in str(e) or 'support-temp-addr' in str(e):
                logger.error(colored(f'{address} | Ошибка: Cкорее всего, ваш адрес не добавлен в белый список для вывода с биржи!', 'light_red'))
            elif 'network is matched' in str(e):
                logger.error(colored(f'{address} | Ошибка: Адрес кошелька не подходит для данной сети!', 'light_red'))
            else:
                logger.error(colored(f'{address} | Ошибка вывода средств ({e})', 'light_red'))
            return False
        except Exception as e:
            logger.error(colored(f"{address} | Unknown error: {e}", 'light_red'))
            return False


def main():
    with open(wallets_file, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        wallets = []
        for row in reader:
            wallets.append(row)

    if flag_wallets_shuffle:
        random.shuffle(wallets)

    for wallet in wallets:
        if withdraw_mode == 1:
            if len(wallet) > 1 and None not in wallet and '' not in wallet:
                status = exchange.withdraw(wallet[0], wallet[1].replace(',', '.'), symbol, network[0], network[1])
            else:
                continue
        elif withdraw_mode == 2:
            status = exchange.withdraw(wallet[0], round(amount,7), symbol, network[0], network[1])
        else:
            status = exchange.withdraw(wallet[0], round(random.uniform(min_amount,max_amount),decimals), symbol, network[0], network[1])
        if not status:
            return
        timing = random.randint(min_delay, max_delay)
        logger.info(colored(f'Сплю {timing} секунд...', 'light_yellow'))
        time.sleep(timing)


def get_proxy():
    with open(proxy_file, 'r') as file:
        proxy = file.read().replace('\n','')
    if not proxy or len(proxy) == 20:
        return None
    proxies = {
        "http": proxy,
        "https": proxy,
    }
    return proxies


if __name__ == "__main__":

    art = text2art(text="CEX  WITHDRAWER", font="standart")
    print(colored(art,'light_blue'))
    art = text2art(text="t.me/cryptogovnozavod", font="cybermedum")
    print(colored(art,'light_cyan'))

    while True:
        if os.path.exists(api_keys_file):
            password = inquirer.prompt([inquirer.Password("password", message=colored("Введите ваш секретный пароль для доступа к данным api-ключей", 'light_yellow'))])['password']
            print()
            cryptographer = PasswordEncryption(password, password[-1:-4:-1])
            with open(api_keys_file, 'r') as f:
                api_keys = cryptographer.decrypt(f.read())
                if not api_keys:
                    print(colored('Неверный пароль! Если забыли пароль, удалите файл encrypted_keys.txt и добавьте все api-ключи заного!', 'light_red'), end = '\n\n')
                    continue
                break
        else:
            print(colored("Придумайте секретный пароль для шифрования данных api-ключей. Запомните его. Для вашей безопасности не используйте простые пароли!", 'light_yellow'))
            password = inquirer.prompt([inquirer.Text("password", message=colored("Введите его тут", 'light_yellow'))])['password']
            if len(password) < 7:
                print(colored('Пароль должен быть не менее 7 символов!', 'light_red'))
                continue
            cryptographer = PasswordEncryption(password, password[-1:-4:-1])
            api_keys = {}
            break

    while True:
        question = [
            inquirer.List(
                "action_type",
                message=colored("Выберите действие", 'light_yellow'),
                choices=[colored("Вывести средства", attrs=['bold', 'blink']), colored("Добавить или обновить api-ключи", attrs=['bold', 'blink']), colored("Справка", attrs=['bold', 'blink'])],
            )
        ]
        action_type = colored(inquirer.prompt(question)['action_type'])[8:-8]

        if 'Справка' in action_type:
            print(colored("Автор: https://t.me/cryptogovnozavod", 'light_cyan'))
            print(colored("Для начала работы необходимо поместить адреса кошельков в files/wallets.csv построчно в ПЕРВЫЙ столбец таблицы.", 'light_cyan'))
            print(colored("Если вы хотите вывести конкретные суммы на каждый кошелек, необходимо указать суммы для вывода ВТОРЫМ столбцом построчно, рядом с адресами.", 'light_cyan'))
            print(colored("API-ключи необходимо будет добавить при первом выводе средств, затем всегда будет возможность обновить их.", 'light_cyan'))
            print(colored("Чтобы вставить API-ключ в поле для ввода в консоли надо использовать правую кнопку мыши, для IDE могут использоваться другие сочетания клавиш.", 'light_cyan'))
            print(colored("Чтобы не провоцировать антифрод бирж и не палить мульты, лучше выбирать большие промежутки времени между выводами средств", 'light_cyan'))
            print(colored("При использовании OKX из РФ, если сайт заблокирован для вашего IP, необходимо добавить прокси в files/proxy.txt в указанном формате.", 'light_cyan'))
            print(colored("Мы НЕ НЕСЕМ ответственности за последствия использования скрипта, все риски всегда на Вас.", 'light_red'), end='\n\n')
            continue

        ex_list = ['binance', 'okx', 'bybit', 'mexc', 'huobi']  
        question = [
            inquirer.List(
                "ex_name",
                message=colored(action_type, 'light_yellow'),
                choices=[colored(ex.upper(), attrs=['bold', 'blink']) for ex in ex_list],
            )
        ]
        ex_name = colored(inquirer.prompt(question)['ex_name']).lower()[8:-8]

        if ex_name == 'okx':
            print(colored('[Информация] Внимание! Если вы находитесь в РФ и сайт OKX заблокирован для вас, для использования API необходимо добавить (иностранный) прокси в files/proxy.txt', 'light_cyan'), end='\n\n')

        if ex_name not in api_keys or 'Добавить' in action_type:
            api_key = inquirer.prompt([inquirer.Password("api_key", message=colored("Вставьте ваш API-ключ (API KEY) для доступа к бирже (right click)", 'light_yellow'))])['api_key']
            print()
            api_secret = inquirer.prompt([inquirer.Password("api_secret", message=colored("Вставьте ваш секретный ключ (SECRET KEY) для доступа к бирже (right click)", 'light_yellow'))])['api_secret']
            print()
            api_keys[ex_name] = {
                    'api_key': api_key, 
                    'api_secret': api_secret,
                    'password': '-',
                }
            with open(api_keys_file, 'w') as f:
                encrypted_data = cryptographer.encrypt(api_keys)
                f.write(encrypted_data)

        if 'Добавить' in action_type:
            print(colored('Данные о ключах успешно обновлены!', 'green', attrs=['bold', 'blink']), end='\n\n')
            continue

        exchange = Exchange(ex_name, api_keys[ex_name]['api_key'], api_keys[ex_name]['api_secret'], api_keys[ex_name]['password'])

        while True:
            symbol = inquirer.prompt([inquirer.Text("symbol", message=colored("Введите символ токена для вывода (Ex. ETH)", 'light_yellow'))])['symbol'].upper()
            print()
            chain_list = exchange.get_withdraw_chains(symbol)
            if not chain_list:
                print()
                continue
            break

        chain_select = [
            inquirer.List(
                "network",
                message=colored("Выберите сеть для вывода", 'light_yellow'),
                choices=[colored(f"{chain[0].upper().ljust(12)}(fee: {f'{chain[1]:.8f}'.rstrip('0').rstrip('.')})", attrs=['bold', 'blink']) for chain in chain_list],
            )
        ]
        network_name = inquirer.prompt(chain_select)['network']
        for i,elem in enumerate(chain_list):
            if elem[0].upper() in network_name:
                network = chain_list[i]

        question = [
            inquirer.List(
                "withdraw_mode",
                message=colored("Суммы для вывода", 'light_yellow'),
                choices=[colored("Взять из файла с кошельками", attrs=['bold', 'blink']), colored("Вывести на все кошельки одинаковую сумму", attrs=['bold', 'blink']), colored("Вывести на все кошельки случайные суммы в некотором диапазоне", attrs=['bold', 'blink'])],
            )
        ]
        withdraw_question = inquirer.prompt(question)['withdraw_mode']
        withdraw_mode = 1 if 'файла' in withdraw_question else 2 if 'одинаковую' in withdraw_question else 3

        while True:
            try:
                if withdraw_mode == 2:
                    amount = float(inquirer.prompt([inquirer.Text("min_amount", message=colored("Введите количество монеты для вывода", 'light_yellow'))])['min_amount'].replace(',', '.').replace(' ', ''))
                    if amount < float(network[2]):
                        print(colored(f'\nМинимальная сумма для вывода в сети {network[0]} на бирже составляет {network[2]} {symbol}!', 'light_red'), end='\n\n')
                        continue
                    print(colored(f'\n[Информация] Выбрано: Биржа - {ex_name.upper()}, Токен - {symbol}, Сеть - {network[0]}, Cумма - {round(amount,7)} {symbol}', 'light_cyan'))
                elif withdraw_mode == 3:
                    min_amount = float(inquirer.prompt([inquirer.Text("min_amount", message=colored("Введите минимальное количество монеты для вывода", 'light_yellow'))])['min_amount'].replace(',', '.').replace(' ', ''))
                    max_amount = float(inquirer.prompt([inquirer.Text("max_amount", message=colored("Введите максимальное количество монеты для вывода", 'light_yellow'))])['max_amount'].replace(',', '.').replace(' ', ''))
                    decimals = int(inquirer.prompt([inquirer.Text("decimals", message=colored("Сколько знаков после запятой использовать? (10.523 = 3 знака)", 'light_yellow'))])['decimals'].replace(',', '.').replace(' ', ''))
                    print(colored(f'\n[Информация] Выбрано: Биржа - {ex_name.upper()}, Токен - {symbol}, Сеть - {network[0]}, Минимальная сумма - {round(min_amount,decimals)} {symbol}, Максимальная сумма - {round(max_amount,decimals)} {symbol}', 'light_cyan'))
                    if min_amount < float(network[2]):
                        print(colored(f'\nМинимальная сумма для вывода в сети {network[0]} на бирже составляет {network[2]} {symbol}!', 'light_red'), end='\n\n')
                        continue
                else:
                    print(colored(f'\n[Информация] Выбрано: Биржа - {ex_name.upper()}, Токен - {symbol}, Сеть - {network[0]}, Cумма - берется из таблицы', 'light_cyan'))
                break
            except ValueError as e:
                print(colored('\nНеверный ввод!', 'light_red'), end='\n\n')

        if ex_name in ('okx','bybit'):
            print(colored(f'[Информация] Данная биржа требует добавления адресов в белый список перед выводом средств.', 'light_cyan'))
        print(colored(f'[Информация] Учтите, что за каждый вывод с суммы/баланса будет удержана комиссия биржи ', 'light_cyan'), end='')
        print(colored(f"{f'{network[1]:.8f}'.rstrip('0').rstrip('.')} {symbol}", 'light_red'), end='')
        print(colored(f'!', 'light_cyan'), end='\n\n')

        question = [
            inquirer.List(
                "correct",
                message=colored("Всё верно?", 'light_yellow'),
                choices=[colored('Да', attrs=['bold', 'blink']), colored('Нет', attrs=['bold', 'blink'])],
            )
        ]
        if 'Нет' in inquirer.prompt(question)['correct']:
            continue

        while True:
            try:
                min_delay = int(inquirer.prompt([inquirer.Text("min_delay", message=colored("Укажите минимальное время задержки между выводами средств (в секундах)", 'light_yellow'))])['min_delay'])
                max_delay = int(inquirer.prompt([inquirer.Text("max_delay", message=colored("Укажите максимальное время задержки между выводами средств (в секундах)", 'light_yellow'))])['max_delay'])
                if min_delay < 5:
                    min_delay = max_delay = 5
                print()
                break
            except ValueError as e:
                print(colored('\nНеверный ввод!', 'light_red'), end='\n\n')

        question = [
            inquirer.List(
                "shuffle",
                message=colored("Перемешать кошельки между собой?", 'light_yellow'),
                choices=[colored('Да', attrs=['bold', 'blink']), colored('Нет', attrs=['bold', 'blink'])],
            )
        ]
        flag_wallets_shuffle = True if 'Да' in inquirer.prompt(question)['shuffle'] else False

        print(colored('[Информация] Начинаю вывод средств...', 'light_cyan'), end='\n\n')
        main()
        print("\n\n")

