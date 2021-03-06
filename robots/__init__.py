import logging

from robots.robot import Robot
from robots.maps import PheMap, BarrierMap
from robots.setting import BOT_NUMS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

phe_map = PheMap()
barrier_map = BarrierMap()
robots_list = []
robots_init_loc = []
robots_await_nodes = {bot_id: [] for bot_id in range(BOT_NUMS)}

for i in range(BOT_NUMS):
    new_bot_node = barrier_map.get_random_node()
    while new_bot_node.loc() in robots_init_loc:
        new_bot_node = barrier_map.get_random_node()
    robots_init_loc.append((new_bot_node.x, new_bot_node.y))
    robots_list.append(Robot(new_bot_node, bot_id=i))
    robots_await_nodes[i] = []

final_map = []

for i in range(BOT_NUMS):
    logger.debug(f'bot #{i} is inited at {robots_list[i].loc()}')
