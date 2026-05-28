
if __name__ == "__main__":
    from user_management.consumer import UserConsumer

    worker = UserConsumer()
    worker.start_consuming()
