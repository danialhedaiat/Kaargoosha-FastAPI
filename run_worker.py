import threading

from account.consumer import AccountConsumer
from loan.consumer import LoanConsumer
from user_management.consumer import UserConsumer


def run(consumer_class):
    consumer = consumer_class()
    consumer.start_consuming()


if __name__ == "__main__":
    user_consumer = threading.Thread(target=run, args=(UserConsumer,), daemon=True)
    loan_consumer = threading.Thread(target=run, args=(LoanConsumer,), daemon=True)
    account_consumer = threading.Thread(target=run, args=(AccountConsumer,), daemon=True)

    user_consumer.start()
    loan_consumer.start()
    account_consumer.start()

    user_consumer.join()
    loan_consumer.join()
    account_consumer.join()
