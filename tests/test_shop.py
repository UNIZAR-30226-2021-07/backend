"""
Tests para las consultas de la tienda de objetos.
"""

from .base import GatovidTestClient


class ShopTests(GatovidTestClient):
    user_data = {
        "email": "test_user1@gmail.com",
        "password": "whatever1",
    }

    def test_buy_board(self):
        resp = self.request_token(self.user_data)
        token = resp.json["access_token"]

        starting_coins = self.request_coins(token)

        item_price = 75
        resp = self.request_shop_buy(item_id=3, item_type="board", token=token)
        self.assertRequestOk(resp)

        end_coins = self.request_coins(token)

        self.assertEqual(end_coins, starting_coins - item_price)

    def test_buy_pic(self):
        resp = self.request_token(self.user_data)
        token = resp.json["access_token"]

        resp = self.request_shop_buy(item_id=3, item_type="profile_pic", token=token)
        self.assertRequestOk(resp)

    def test_wrong_input(self):
        resp = self.request_token(self.user_data)
        token = resp.json["access_token"]

        resp = self.request_shop_buy(item_id=3, item_type="gato", token=token)
        self.assertRequestErr(resp, 400)
        resp = self.request_shop_buy(item_id=999, item_type="board", token=token)
        self.assertRequestErr(resp, 400)
        resp = self.request_shop_buy(item_id=-1, item_type="board", token=token)
        self.assertRequestErr(resp, 400)

    def test_wrong_input_types(self):
        resp = self.request_token(self.user_data)
        token = resp.json["access_token"]

        resp = self.request_shop_buy(item_id="3", item_type="board", token=token)
        self.assertRequestOk(resp)

    def test_not_enough_money(self):
        resp = self.request_token(self.user_data)
        token = resp.json["access_token"]

        start_coins = self.request_coins(token)

        resp = self.request_shop_buy(item_id=5, item_type="board", token=token)
        self.assertRequestErr(resp, 400)

        end_coins = self.request_coins(token)
        self.assertEqual(end_coins, start_coins)

    def test_already_bought(self):
        resp = self.request_token(self.user_data)
        token = resp.json["access_token"]

        resp = self.request_shop_buy(item_id=2, item_type="board", token=token)
        self.assertRequestOk(resp)

        start_coins = self.request_coins(token)

        resp = self.request_shop_buy(item_id=2, item_type="board", token=token)
        self.assertRequestErr(resp, 400)

        end_coins = self.request_coins(token)
        self.assertEqual(end_coins, start_coins)
