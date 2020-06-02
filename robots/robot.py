import numpy as np
from typing import Union, List

from robots.setting import (
    BOT_COMMUNICATE_RANGE,
    BOT_MOVING_RANGE,
    PROFIT_RATIO,
    PHE_RATIO,
    BOT_SENSOR_RANGE,
)

import robots
from robots.maps import ExploreMap, PheMap, Node, BarrierMap


class Robot:

    def __init__(self, node: Union[Node, tuple], bot_id: int):
        if isinstance(node, Node):
            self.node = node
        elif isinstance(node, tuple):
            self.node = Node(node)
        else:
            raise TypeError
        self.bot_id = bot_id
        self.moving_range = BOT_MOVING_RANGE
        self.sensor_range = BOT_SENSOR_RANGE
        self.comm_range = BOT_COMMUNICATE_RANGE
        self.loc_barrier_map = ExploreMap()
        self.loc_explore_map = ExploreMap()
        self.moving_path = []
        self.explore_node_list = []

    def loc(self) -> tuple:
        return self.node.loc()

    def get_moving_profit(self, node: Node) -> Union[float, None]:
        """
        针对任务点的出价函数
        :param node: 任务点
        :return: 出价值，None表示不可达
        """
        if self.get_accessibility(node):
            moving_cost = self.get_manha_distance(node)
            phe = self.get_phe_level(node)
            explore_profit = self.get_explore_profit(node)
            r = np.exp(
                PROFIT_RATIO * explore_profit + (1 - PROFIT_RATIO) * (
                        moving_cost + PHE_RATIO * phe
                )
            )
            return r
        else:
            return None

    def get_manha_distance(self, node: Node) -> int:
        """
        返回自身和目标点之间的曼哈顿距离
        :param node: 另一个点
        :return: 曼哈顿距离
        """
        return np.abs(self.node.x - node.x) + np.abs(self.node.y - node.y)

    def get_phe_level(self, node: Node, phe_map: PheMap) -> float:
        """
        得到信息素水平
        :param node:
        :param phe_map: 全局信息素水平
        :return:
        """
        return phe_map.get_phe(self.node, node)

    def get_explore_profit(self, node: Node) -> int:
        """
        简化处理，考虑到达任务点确认点增加情况
        :param node:
        :return:
        """
        new_explore_node = 0
        for i in range(node.x - self.sensor_range, node.x + self.sensor_range + 1):
            for j in range(node.y - self.sensor_range, node.y + self.sensor_range + 1):
                if self.loc_explore_map[i, j] == 0:
                    new_explore_node += 1

        return new_explore_node

    def get_accessibility(self, node: Node) -> bool:
        """
        对任务点的探索可达性
        :param node:
        :return: bool
        """
        # todo 任务点过远问题
        return np.sqrt((self.node.x - node.x) ** 2 + (self.node.y - node.y) ** 2) < self.moving_range

    def update_loc_map(self, bot):
        self.loc_explore_map |= bot.loc_explore_map
        self.loc_barrier_map |= bot.loc_barrier_map

    def is_finished(self):
        """
        检验本地探索地图，判断地图探索是否完成
        :return: bool
        """
        return self.loc_explore_map.is_finished()

    def get_await_node(self) -> Node:
        """
        边界点中找寻下一个任务
        :return: 对自己最优任务点
        """
        x, y = self.loc()
        node_list = []
        for i in range(x - self.moving_range, x + self.moving_range + 1):
            for j in range(y - self.moving_range, y + self.moving_range + 1):
                distance = np.sqrt((x - i) ** 2 + (y - j) ** 2)
                if self.loc_explore_map[i, j] == 0 and distance <= self.moving_range:
                    node_list.append((Node((x, y)), distance))
    
        if node_list:
            return min(node_list, key=lambda k: k[1])[0]
        else:
            """
            通信范围内无可探测点
            """
            pass

    def release_node_and_wait_for_buyer(self, current_await_node: List) -> (int, Node):
        """
        拍卖执行过程
        :param current_await_node:
        :return: 执行者编号 rob_id
        """

        target = self.get_await_node()
        target_profit = self.get_moving_profit(target)
        node_list = [(target, target_profit)]
        await_list = [(node, self.get_moving_profit(node)) for node in current_await_node]

        node, profit = sorted(node_list+await_list, key=lambda k: k[1], reverse=True)[0]

        executor = self.bot_id
        for bot in robots.robots_list:
            if bot.bot_id != self.bot_id:
                self.update_loc_map(bot)
                if self.get_accessibility(bot.node):
                    bot_profit = bot.get_moving_profit(node)
                    if bot_profit > profit:
                        executor = bot.bot_id

        if node in current_await_node:
            current_await_node.pop(current_await_node.index(node))

        return executor, node, current_await_node
    
    def explore(self):
        """
        对探索地图进行更新，传感器范围内探索，移动一个单位后执行，包括未知点探索和信息素更新
        :return:
        """
        x, y = self.loc()
        # 信息素更新
        robots.phe_map.update_phe(self.node)
        # 探索
        for i in range(x - self.sensor_range, x + self.sensor_range + 1):
            for j in range(y - self.sensor_range, y + self.sensor_range + 1):
                distance = np.sqrt((x - i) ** 2 + (y - j) ** 2)
                if distance <= self.sensor_range:
                    self.loc_explore_map.update(Node((i, j)))
                    if robots.barrier_map[i, j]:
                        self.loc_barrier_map.update(Node((i, j)))
    
    def find_way(self, nodes: List):
        """
        用于找到自身到目标点的移动轨迹
        :param nodes:
        :param target: 目标任务点
        :return:
        """
        sorted_nodes = max(nodes, key=lambda k: self.get_moving_profit(k))
        target_node = sorted_nodes[0]
        # D*算法，得到路径序列
        self.explore_node_list = [1, 2, 2, 3, 3]

    def move(self, next_node: Node):
        """
        机器人执行移动，并对移动后的点执行探索，探索包括未知点发现和信息素更新
        :param next_node: 下一个移动点
        :return:
        """
        if self.loc_barrier_map.status(next_node):
            return 0
        else:
            self.node = next_node
            self.moving_path.append(next_node)
            self.explore()
            return 1

    def run(self) -> bool:
        """
        这里的执行过程，判断是否能够进行下一步移动，如果不能移动，重新执行寻路算法，更新移动路径，并重新执行移动
        :return:
        """
        if self.explore_node_list:
            if self.move(self.explore_node_list.pop(0)):
                self.find_way(self.explore_node_list[-1])
                self.move(self.explore_node_list.pop(0))
            return True
        else:
            return False
