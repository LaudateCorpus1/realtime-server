from common import service_const, gv
# from common.service_const import DISPATCHER_SERVICE
from core.util import UtilApi
from core.util.UtilApi import Singleton
from core.util.performance.cpu_load_handler import AvgCpuLoad
from server_entity.ServerEntity import ServerEntity


LOAD_REPORT_INTERVAL = 8


class LoadReporter(ServerEntity):

    def __init__(self):
        super().__init__()
        self._avg_load = AvgCpuLoad()
        self.timer_hub.call_later(LOAD_REPORT_INTERVAL, self.report_load, repeat_count=-1)

    def report_load(self):
        try:
            dispatcher_service_addr = UtilApi.get_service_info(service_const.DISPATCHER_SERVICE)
            if dispatcher_service_addr:
                self.call_remote_method(
                    "report_load",
                    [gv.etcd_tag, gv.game_server_name, gv.local_ip, gv.local_port,
                        self._avg_load.get_avg_cpu_by_period(10)],
                    rpc_remote_entity_type="LoadCollector", ip_port_tuple=dispatcher_service_addr)
                # print(f"report_server_load: {self._avg_load.get_avg_cpu_by_period(10)}")
            else:
                self.logger.error("can not find dispatcher_service_addr")
        except:
            self.logger.log_last_except()