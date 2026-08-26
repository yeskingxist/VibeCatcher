from auth import auth_manager
import logging, traceback

auth_manager.load_session()
auth_manager.client.request_logger.setLevel(logging.WARNING)

try:
    res = auth_manager.client.private_request('accounts/current_user/?edit=true')
    print(res['user']['username'])
except Exception as e:
    print(e)
    traceback.print_exc()
