from __future__ import print_function, unicode_literals
import re
import os

from enum import Enum
import sqlite3
from database.database import Database
from typing import Tuple, List, Dict, Any

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.validator import EmptyInputValidator
from prompt_toolkit.validation import ValidationError, Validator

PHONE_TYPES: List[Tuple[str, int]] = [
    ("Basic", 250),
    ("Standard", 450),
    ("Superior", 950)
]
VAT_RATE: float = 0.2
PHONE_CHOICES: List[Choice] = [ Choice(value=x[0], name=f"{x[0]} £{x[1]}") for x in PHONE_TYPES ]

class PhoneOptions(Enum):
    OPTION_A    = 1
    OPTION_B    = 2
    OPTION_NULL = 3

class PhoneNumberValidator(Validator):
    def __init__(self, message: str = "Phone number is invalid"):
        self._message = message

    def validate(self, document):
        if not len(document.text) > 0:
            raise ValidationError(
                message=self._message,
                cursor_position=document.cursor_position,
            )
        
        if not re.match(r"^(07\d{8,12}|447\d{7,11})$", document.text):
            raise ValidationError(message=self._message, cursor_position=document.cursor_position)

class CommandSelectValidator(Validator):
    def __init__(self, message: str = "Incorrect Command"):
        self._message = message

    def validate(self, document):
        if int(document.text) not in [1, 2]:
            raise ValidationError(
                message=self._message,
                cursor_position=document.cursor_position,
            )

class QuantityValidator(Validator):
    def validate(self, document):
        if not len(document.text) > 0:
            raise ValidationError(
                message="Error Quantity cannot be 0",
                cursor_position=document.cursor_position,
            )
        
        # https://inquirerpy.readthedocs.io/en/latest/_modules/InquirerPy/validator.html#NumberValidator
        try:
            quantity = int(document.text)
        except ValueError:
            raise ValidationError(
                message="Error: Please enter a valid number.",
                cursor_position=document.cursor_position,
            )

        if quantity < 5 or quantity > 100: # shouldn't happen
            raise ValidationError(
                message="Error: Quantity must be between 5 and 100.",
                cursor_position=document.cursor_position,
            )

        if quantity % 5 != 0:
            raise ValidationError(
                message="Error: Quantity must be in intervals of 5.",
                cursor_position=document.cursor_position,
            )

def calculate_cost(phone_type: str, quantity: int, options: int) -> Tuple[float, float, float]:
    """Calculate the total cost

    Args:
        phone_type (str): Phone type: Basic, Standard, Superior
        quantity (int): Quantity of phones customer is purchasing
        options (int): Optional phone options

    Raises:
        ValueError: if phone_type is incorrect

    Returns:
        Tuple[float, float, float]: The total cost before VAT, Calculated VAT, Total cost + VAT
    """

    # find the base cost of the selected phone type
    base_cost = next((cost for name, cost in PHONE_TYPES if name == phone_type), None)

    if base_cost is None:
        raise ValueError(f"Invalid phone type selected: {phone_type}")

    quantity = int(quantity)
    options = int(options)

    setup_cost = {
        PhoneOptions.OPTION_A.value: 30,
        PhoneOptions.OPTION_B.value: 50,
        PhoneOptions.OPTION_NULL.value: 0
    }[options]

    total_cost_before_vat = (base_cost + setup_cost) * quantity

    vat = total_cost_before_vat * VAT_RATE
    total_cost_with_vat = total_cost_before_vat + vat

    return round(float(total_cost_before_vat), 2), round(float(vat), 2), round(float(total_cost_with_vat), 2)

def insert_invoice(company_name: str, company_num: str, smart_phone_type: str,
                   selected_option: int, quantity_num: int, 
                   vat: float, total_cost: float, total_with_vat: float) -> None:
    """Insert an invoice into the database

    Args:
        company_name (str): Company name to be inserted has to be unique
        company_num (str): Company phone number
        smart_phone_type (str): Phone type [Basic, Standard, Superiror]
        selected_option (int): Selected optional options
        quantity_num (int): Quantity of phone's customer requires
        vat (float): Calculated VAT
        total_cost (float): Total cost
        total_with_vat (float): Total cost + VAT
    """
    data: Dict[str, str] = {
        "company_name": company_name,
        "company_num": company_num,
        "phone_type": smart_phone_type,
        "phone_opt": selected_option,
        "quantity": quantity_num,
        "vat": vat,
        "total_cost": total_cost,
        "total_cost_vat": total_with_vat,
    }

    try:
        with Database("customers.db") as db:
            db.insert("invoices", data)
    except sqlite3.IntegrityError as e:
        print(f"Error inserting {e}")

def handle_customer() -> None:
    """Handles user input """
    company_name: str = inquirer.text(message="Company Name =>", validate=EmptyInputValidator()).execute()
    company_num: str = inquirer.text(message="Company phone number => ", validate=PhoneNumberValidator()).execute()

    smart_phone_type: Any = inquirer.select(
        message="Select phone type =>",
        choices=PHONE_CHOICES,
        transformer=lambda result: "Selected %s phone type" % (result),
        default=None
    ).execute()

    smart_phone_options: Any = inquirer.checkbox(
        message="Smartphone options (Optional) =>",
        choices=[
            Choice(value=PhoneOptions.OPTION_A.value, name="Option A (5 apps)"),
            Choice(value=PhoneOptions.OPTION_B.value, name="Option B (10 apps)"),
            Choice(value=PhoneOptions.OPTION_NULL.value, name="None")
        ],
        validate=lambda result: len(result) == 1,
        transformer=lambda result: "You picked %s option" % (result),
        invalid_message="Please choose one option",
        instruction="(select only one option)"
    ).execute()

    # select the option in integer format from the enum
    selected_option: int = int(smart_phone_options[0]) if smart_phone_options else PhoneOptions.OPTION_NULL.value

    quantity_num: Any = inquirer.number(
        message="Quantity of phones =>",
        min_allowed=5,
        max_allowed=100,
        instruction="(min=5, max=100)",
        validate=QuantityValidator()
    ).execute()

    try:
        # all floats
        total_cost, vat, total_with_vat = calculate_cost(smart_phone_type, quantity_num, selected_option)
        print(
            "=[NEW INVOICE]=\n"
            f"Company Name: {company_name}\n"
            f"Company Num: {company_num}\n"
            f"Smart Phone Type: {smart_phone_type}\n"
            f"Smart Phone Option: {selected_option}\n"
            f"Quantity: {quantity_num}\n"
            f"Total Cost: £{total_cost:.2f}\n"
            f"VAT: £{vat:.2f}\n"
            f"Total Cost including VAT: £{total_with_vat:.2f}"
            )
        
        insert_invoice(company_name, company_num, smart_phone_type, 
                       selected_option, quantity_num,
                        vat, total_cost, total_with_vat)
        
        input()
        
    except ValueError as e:
        print(f"Error => {e}")
        input()

def pretty_print_invoices(invoices: List[Tuple]):
    """Pretty print and make a table to display the invoices

    Args:
        invoices (List[Tuple]): List of invoices for example (row[0], row[1], row[2], ...)
    """
    if not invoices:
        print("No invoices found.")
        return

    # print a table like
    print("ID | Company Name | Company Num | Phone Type | Phone Option | Quantity | VAT    | Total Cost | Total Cost with VAT")
    print("-" * 115)  # line for separation

    for invoice in invoices:
        invoice_id, company_name, company_num, phone_type, phone_opt, quantity, vat, total_cost, total_with_vat = invoice
        print(f"{invoice_id:<2} | {company_name:<13} | {company_num:<11} | {phone_type:<10} | {phone_opt:<12} | "
              f"{quantity:<8} | £{vat:<6.2f} | £{total_cost:<10.2f} | £{total_with_vat:<15.2f}")
        
    input()


def read_all_invoices() -> None:
    with Database("customers.db") as db:
        result = db.search("invoices")
        pretty_print_invoices(result)

def input_invoice():
    print("====== MASA Telecommunications =====")
    while True:
        os.system("cls")
        select = inquirer.select(
            message="Choose function =>",
            choices=[
                Choice(value=1, name="Read all invoices"),
                Choice(value=2, name="Create new invoice")
            ],
            validate=CommandSelectValidator(),
            default=None
        ).execute()

        match select:
            case 1: 
                read_all_invoices()
            case 2:
                handle_customer()
            case _:
                raise ValueError("Incorrect command") # shouldn't get to this due to validator

def init_database() -> None:
    with Database("customers.db") as db:
        db.cursor.execute(
"""
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL UNIQUE,
    company_num TEXT NOT NULL,
    phone_type TEXT NOT NULL,
    phone_opt INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    vat FLOAT NOT NULL,
    total_cost FLOAT NOT NULL,
    total_cost_vat FLOAT NOT NULL
)
""")

def main() -> None:
    init_database()

    input_invoice()


if __name__ == "__main__":

    main()
