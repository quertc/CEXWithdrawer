import time
import random
import os
import csv
from sys import stderr

import ccxt
import inquirer 
from inquirer.themes import load_theme_from_dict as loadth
from termcolor import colored
from loguru import logger
from art import text2art

from modules.cipher import PasswordEncryption


wallets_file = 'files/wallets.csv'
api_keys_file = 'files/encrypted_keys.txt'
done_file = 'files/done.csv'
log_file = 'logs/log.log'


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
            'proxies': None,
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
            elif self.name == 'kucoin':
                if coin_data['withdraw'] == True:
                    network_name = coin_data['id']
                    withdraw_fee = float(coin_data['info']['withdrawalMinFee'])
                    withdraw_min = float(coin_data['info']['withdrawalMinSize'])
                    chains.append([network_name, withdraw_fee, withdraw_min])
            else:
                for chain in coin_data['networks'].values():
                    if chain['withdraw'] == True:
                        network_name = chain['id'].split(f'{symbol}-')[1]
                        withdraw_fee = float(chain['fee'])
                        withdraw_min = float(chain['limits']['withdraw']['min'])
                        chains.append([network_name, withdraw_fee, withdraw_min])
            return chains
        except KeyError as e:
            print(colored(f"There is no such symbol on CEX! Try entering again.", 'light_red'))
            return False
        except Exception as e:
            if 'Invalid API-key' in str(e) or 'Unmatched IP' in str(e):
                print(colored(f"Error: Most likely your current IP address is not on the whitelist for withdrawals or your API key has expired!", 'light_red'))
            elif 'GET' in str(e):
                print(colored(f"Error: CEX is temporarily unavailable, either not available at your location.", 'light_red'))
            else:
                print(colored(f"Unknown error in obtaining available withdrawal networks: {e}", 'light_red'))
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
            logger.success(colored(f"{address} | Successfully withdrawn {amount_to_withdrawal} {symbol_to_withdraw}", 'light_green'))
            return True
        except ccxt.InsufficientFunds as e:
            logger.error(colored(f'{address} | Error: Insufficient funds on the balance!', 'light_red'))
            return False
        except ccxt.ExchangeError as e:
            if 'not equal' in str(e) or 'not whitelisted' in str(e) or 'support-temp-addr' in str(e):
                logger.error(colored(f'{address} | Error: Most likely, your address has not been added to the whitelist for withdrawal from the CEX!', 'light_red'))
            elif 'not authorized' in str(e):
                logger.error(colored(f'{address} | Error: Most likely, your API key has expired or does not have access to withdraw funds!', 'light_red'))
            elif 'network is matched' in str(e):
                logger.error(colored(f'{address} | Error: The wallet address is not suitable for this network!', 'light_red'))
            else:
                logger.error(colored(f'{address} | Withdrawal error ({e})', 'light_red'))
            return False
        except Exception as e:
            logger.error(colored(f"{address} | Unknown error: {e}", 'light_red'))
            return False


def main():
    done_wallets = set()
    skipped_wallets = 0

    if os.path.exists(done_file):
        with open(done_file, newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            for row in reader:
                done_wallets.add(row[0])

    with open(wallets_file, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        wallets = []
        for row in reader:
            if row[0] in done_wallets:
                skipped_wallets += 1
                continue
            wallets.append(row)

    logger.info(f'Skipped ({skipped_wallets}) wallets where funds have already been withdrawn.')

    if flag_wallets_shuffle:
        random.shuffle(wallets)

    for wallet in wallets:
        status = False
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
        
        if status:
            with open(done_file, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                writer.writerow(wallet)

        timing = random.randint(min_delay, max_delay)
        logger.info(colored(f'Sleeping {timing} seconds...', 'light_yellow'))
        time.sleep(timing)



if __name__ == "__main__":

    art = text2art(text="CEX  WITHDRAWER", font="standart")
    print(colored(art,'light_blue'))

    theme = {
        "Question": {
            "brackets_color": "bright_yellow"
        },
        "List": {
            "selection_color": "bright_blue"
        }
    }

    while True:
        if os.path.exists(api_keys_file):
            password = inquirer.prompt([inquirer.Password("password", message=colored("Enter your secret password to access api key data", 'light_yellow'))])['password']
            print()
            cryptographer = PasswordEncryption(password, password[-1:-4:-1])
            with open(api_keys_file, 'r') as f:
                api_keys = cryptographer.decrypt(f.read())
                if not api_keys:
                    print(colored('Incorrect password! If you forgot your password, delete the encrypted_keys.txt file and add all api keys again!', 'light_red'), end = '\n\n')
                    continue
                break
        else:
            print(colored("Create a secret password to encrypt the api key data. Remember it. For your safety, do not use simple passwords!", 'light_yellow'))
            password = inquirer.prompt([inquirer.Text("password", message=colored("Enter it here", 'light_yellow'))])['password']
            if len(password) < 7:
                print(colored('The password must be at least 7 characters!', 'light_red'))
                continue
            cryptographer = PasswordEncryption(password, password[-1:-4:-1])
            api_keys = {}
            break

    while True:
        question = [
            inquirer.List(
                "action_type",
                message=colored("Select an action", 'light_yellow'),
                choices=["Withdraw funds", "Add or update api keys", "Reference"],
            )
        ]
        action_type = inquirer.prompt(question,theme=loadth(theme))['action_type']

        if action_type == 'Reference':
            print(colored("To get started, put the wallet addresses in files/wallets.csv line by line into the FIRST column of the table.", 'light_cyan'))
            print(colored("If you want to withdraw specific amounts to each wallet, you should specify the amounts to be withdrawn in the SECOND column, line by line, next to the addresses.", 'light_cyan'))
            print(colored("API keys will need to be added when you first withdraw funds, then you will always have the opportunity to update them.", 'light_cyan'))
            print(colored("To insert an API key into the input field in the console you should use the right mouse button, other keyboard shortcuts can be used for IDE.", 'light_cyan'))
            print(colored("In order not to provoke CEXes antifraud and not to reveal multi-accounts, it is better to choose long time intervals between withdrawals of funds.", 'light_cyan'))
            print(colored("We are NOT responsible for the consequences of using the script, all risks are always on you.", 'light_red'), end='\n\n')
            continue

        ex_list = ['binance', 'okx', 'bybit', 'mexc', 'huobi', 'kucoin']  
        question = [
            inquirer.List(
                "ex_name",
                message=colored(action_type, 'light_yellow'),
                choices=[ex.upper() for ex in ex_list],
            )
        ]
        ex_name = inquirer.prompt(question,theme=loadth(theme))['ex_name'].lower()

        if ex_name not in api_keys or 'Add' in action_type:
            api_key = inquirer.prompt([inquirer.Password("api_key", message=colored("Insert your API key (API KEY) to access the exchange (right click)", 'light_yellow'))])['api_key']
            print()
            api_secret = inquirer.prompt([inquirer.Password("api_secret", message=colored("Insert your secret key (SECRET KEY) to access the exchange (right click)", 'light_yellow'))])['api_secret']
            print()
            p = False
            if ex_name in ('okx','kucoin'):
                p = inquirer.prompt([inquirer.Password("p", message=colored("Insert your api password (api-passphrase) to access the exchange (right click)", 'light_yellow'))])['p']
                print()
            api_keys[ex_name] = {
                    'api_key': api_key, 
                    'api_secret': api_secret,
                    'password': p if p else '-',
                }
            with open(api_keys_file, 'w') as f:
                encrypted_data = cryptographer.encrypt(api_keys)
                f.write(encrypted_data)

        if 'Add' in action_type:
            print(colored('Key data has been successfully updated!', 'light_green'), end='\n\n')
            continue

        exchange = Exchange(ex_name, api_keys[ex_name]['api_key'], api_keys[ex_name]['api_secret'], api_keys[ex_name]['password'])

        while True:
            symbol = inquirer.prompt([inquirer.Text("symbol", message=colored("Enter the token symbol for withdrawal (Ex. ETH)", 'light_yellow'))])['symbol'].upper()
            print()
            chain_list = exchange.get_withdraw_chains(symbol)
            if not chain_list:
                print()
                continue
            break

        chain_select = [
            inquirer.List(
                "network",
                message=colored("Select network for withdrawal", 'light_yellow'),
                choices=[f"{chain[0].upper().ljust(12)}(fee: {f'{chain[1]:.8f}'.rstrip('0').rstrip('.')})" for chain in chain_list],
            )
        ]
        network_name = inquirer.prompt(chain_select,theme=loadth(theme))['network']
        for i,elem in enumerate(chain_list):
            if elem[0].upper() == network_name.split('(fee')[0].rstrip(' '):
                network = chain_list[i]

        question = [
            inquirer.List(
                "withdraw_mode",
                message=colored("Amounts to be withdrawn", 'light_yellow'),
                choices=["Take from the file with wallets", "Withdraw the same amount to all wallets", "Withdraw random amounts in some range to all wallets"],
            )
        ]
        withdraw_question = inquirer.prompt(question,theme=loadth(theme))['withdraw_mode']
        withdraw_mode = 1 if 'file' in withdraw_question else 2 if 'same' in withdraw_question else 3

        while True:
            try:
                if withdraw_mode == 2:
                    amount = float(inquirer.prompt([inquirer.Text("min_amount", message=colored("Enter the amount of token to withdraw", 'light_yellow'))])['min_amount'].replace(',', '.').replace(' ', ''))
                    if amount < float(network[2]):
                        print(colored(f'\nThe minimum amount for withdrawal on the {network[0]} network on the exchange is {network[2]} {symbol}!', 'light_red'), end='\n\n')
                        continue
                    print(colored(f'\n[Info] Selected: Exchange - {ex_name.upper()}, Token - {symbol}, Network - {network[0]}, Amount - {round(amount,7)} {symbol}', 'light_cyan'))
                elif withdraw_mode == 3:
                    min_amount = float(inquirer.prompt([inquirer.Text("min_amount", message=colored("Enter the minimum amount of token to withdraw", 'light_yellow'))])['min_amount'].replace(',', '.').replace(' ', ''))
                    max_amount = float(inquirer.prompt([inquirer.Text("max_amount", message=colored("Enter the maximum amount of token to withdraw", 'light_yellow'))])['max_amount'].replace(',', '.').replace(' ', ''))
                    decimals = int(inquirer.prompt([inquirer.Text("decimals", message=colored("How many decimal places to use? (10.523 = 3 decimal places)", 'light_yellow'))])['decimals'].replace(',', '.').replace(' ', ''))
                    if round(min_amount,decimals) > min_amount or round(min_amount,decimals) == 0:
                        print(colored(f'\nToo much rounding of the number, add more decimal places!', 'light_red'), end='\n\n')
                        continue
                    print(colored(f'\n[Info] Token - {symbol}, Network - {network[0]}, Amounts - from {round(min_amount,decimals)} {symbol} to {round(max_amount,decimals)} {symbol}, Example - {round(random.uniform (min_amount,max_amount),decimals)}', 'light_cyan'))
                    if min_amount < float(network[2]):
                        print(colored(f'\nThe minimum amount for withdrawal on the {network[0]} network on the exchange is {network[2]} {symbol}!', 'light_red'), end='\n\n')
                        continue
                else:
                    print(colored(f'\n[Info] Selected: Exchange - {ex_name.upper()}, Token - {symbol}, Network - {network[0]}, Amount - taken from the table', 'light_cyan'))
                break
            except ValueError as e:
                print(colored('\nInvalid input!', 'light_red'), end='\n\n')

        if ex_name in ('okx','bybit'):
            print(colored(f'[Info] This exchange requires addresses to be added to the whitelist before withdrawing funds.', 'light_cyan'))
        print(colored(f'[Info] Please note that exchange commission will be deducted from the amount/balance for each withdrawal ', 'light_cyan'), end='')
        print(colored(f"{f'{network[1]:.8f}'.rstrip('0').rstrip('.')} {symbol}", 'light_red'), end='')
        print(colored(f'!', 'light_cyan'), end='\n\n')

        question = [
            inquirer.List(
                "correct",
                message=colored("Is that right?", 'light_yellow'),
                choices=['Yes', 'No'],
            )
        ]
        if inquirer.prompt(question,theme=loadth(theme))['correct'] == 'No':
            continue

        while True:
            try:
                min_delay = int(inquirer.prompt([inquirer.Text("min_delay", message=colored("Specify the minimum delay time between withdrawals (in seconds)", 'light_yellow'))])['min_delay'])
                max_delay = int(inquirer.prompt([inquirer.Text("max_delay", message=colored("Specify the maximum delay time between withdrawals (in seconds)", 'light_yellow'))])['max_delay'])
                if min_delay < 5:
                    min_delay = max_delay = 5
                print()
                break
            except ValueError as e:
                print(colored('\nInvalid input!', 'light_red'), end='\n\n')

        question = [
            inquirer.List(
                "shuffle",
                message=colored("Shuffle the wallets amongst themselves?", 'light_yellow'),
                choices=['Yes', 'No'],
            )
        ]
        flag_wallets_shuffle = True if inquirer.prompt(question,theme=loadth(theme))['shuffle'] == 'Yes' else False

        print(colored('[Info] Beginning withdrawal...', 'light_cyan'), end='\n\n')
        main()
        print("\n\n")


