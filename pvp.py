import ipaddress
import logging
import pathlib
import random
import string
import sys
from argparse import Namespace
from typing import TYPE_CHECKING, AsyncIterator

import eth_keys
import trio
from async_service import Service, TrioManager, as_service, background_trio_service
from ddht import constants, v5_1
from ddht.boot_info import BootInfo
from ddht.v5_1.app import Application
from eth_enr import ENR
from eth_utils import decode_hex, encode_hex, keccak

if TYPE_CHECKING:
    import signal  # noqa: F401

from raiden.utils.keys import privatekey_to_address

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

n = Namespace()

random.seed(42)


def make_bytes(length: int):
    return bytes("".join(random.choice(string.printable) for _ in range(length)), encoding="utf-8")


pk_api = eth_keys.KeyAPI(backend=eth_keys.backends.NativeECCBackend())

disco_private_keys = [pk_api.PrivateKey(make_bytes(32)) for _ in range(5)]
raiden_private_keys = [pk_api.PrivateKey(make_bytes(32)) for _ in range(5)]


def make_node_id(private_key):
    return keccak(pk_api.PublicKey.from_private(private_key).to_bytes())


lookup_table = dict()
for i in range(5):
    eth_address = privatekey_to_address(raiden_private_keys[i].to_bytes())
    lookup_table[eth_address] = make_node_id(disco_private_keys[i])


print(" ".join([encode_hex(address) for address in lookup_table.keys()]))

ethereum_address = sys.argv[1]


pk_idx = list(lookup_table.keys()).index(decode_hex(ethereum_address))
pk = disco_private_keys[pk_idx]
boot = BootInfo(
    protocol_version=constants.ProtocolVersion.v5_1,
    base_dir=pathlib.Path("."),
    port=23456 + pk_idx,
    listen_on=ipaddress.IPv4Address("0.0.0.0"),
    bootnodes=[ENR.from_repr(_) for _ in v5_1.constants.DEFAULT_BOOTNODES],
    private_key=pk,
    is_ephemeral=True,
    is_upnp_enabled=True,
    is_rpc_enabled=True,
    ipc_path=pathlib.Path("ddht.ipc"),
)

n.session_cache_size = 1024


async def _main():
    async with background_trio_service(TrioCommService()) as manager:
        await manager.wait_finished()


class BootService(Service):
    async def run(self) -> None:
        import signal  # noqa: F811

        with trio.open_signal_receiver(signal.SIGTERM, signal.SIGINT) as signal_aiter:
            ready = trio.Event()
            self.manager.run_daemon_task(self._monitor_signals, ready, signal_aiter)
            # this is needed to give the async iterable time to be entered.
            await ready.wait()

            # imports are triggered at this stage.
            await _main()

            import logging

            logger = logging.getLogger("ddht")
            logger.info("Stopping: Application Exited")
            self.manager.cancel()

    async def _monitor_signals(
        self, ready: trio.Event, signal_aiter: AsyncIterator["signal.Signals"]
    ) -> None:
        import logging
        import signal  # noqa: F811

        ready.set()
        async for sig in signal_aiter:
            logger = logging.getLogger()

            if sig == signal.SIGTERM:
                logger.info("Stopping: SIGTERM")
            elif sig == signal.SIGINT:
                logger.info("Stopping: CTRL+C")
            else:
                logger.error("Stopping: unexpected signal: %s:%s", sig.value, sig.name)

            self.manager.cancel()


def _boot() -> None:
    try:
        manager = TrioManager(BootService())

        trio.run(manager.run)
    except KeyboardInterrupt:
        import logging
        import sys

        logger = logging.getLogger()
        logger.info("Stopping: Fast CTRL+C")
        sys.exit(2)
    else:
        import sys

        sys.exit(0)


queue = []

print(lookup_table)
class TrioCommService(Service):

    async def run(self):
        # run ddht as sub_task
        application = Application(n, boot)
        sub_task = TrioManager(application)
        self.manager.run_task(sub_task.run)

        success = False

        async def lookup(receiver) -> ENR:
            node_id = lookup_table.get(receiver)
            print(" >>>>>>> ", encode_hex(node_id))
            if node_id is not None:
                async with application.network.recursive_find_nodes(
                    target=node_id
                ) as iterator:
                    async for enr in iterator:
                        print("======>    ", encode_hex(enr.node_id))
                        if enr.node_id == node_id:
                            success = True
                            print(enr)


        while not success:
            print("enter")
            await trio.sleep(2)
            await lookup(decode_hex("0xf689a063aed386b17a57ed1f76400f22341ff5cc"))
            print("fail")

        def handle(messages_queues):
            for queue in messages_queues:
                receiver_address = queue.queue_identifier.recipient
                if queue.messages:
                    node = lookup(receiver)
                for message in queue.messages:
                    self.send(message)



# class DDHTTransport:
#     def send_async(self, message_queues) -> None:
#         for queue in message_queues:

#     def send(self, receiver, message):


# def GeventCommGreenlet():


if __name__ == "__main__":
    import pdb

    try:
        _boot()
    except:
        pdb.post_mortem()
