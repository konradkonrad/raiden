# -*- coding: utf-8 -*-
from raiden.transfer.architecture import State
# pylint: disable=too-few-public-methods,too-many-arguments,too-many-instance-attributes


class RouteState(State):
    """ Route state.

    Args:
        state (string): The current state of the route (available or
            unavailable).
        node_address (address): The address of the next_hop.
        capacity (int): The current available balance that can be transferred
            through `node_address`.
        settle_timeout (int): The settle_timeout of the channel set in the
            smart contract.
        reveal_timeout (int): The channel configured reveal_timeout.
    """

    valid_states = (
        'unavailable',
        'avaiable',
    )

    def __init__(self,
                 state,
                 node_address,
                 capacity,
                 settle_timeout,
                 reveal_timeout):

        if state not in self.valid_states:
            raise ValueError('invalid value for state')

        self.state = state
        self.node_address = node_address
        self.capacity = capacity  # TODO: rename to available_balance
        self.settle_timeout = settle_timeout
        self.reveal_timeout = reveal_timeout


class AvailableRoutesState(State):
    """ Routing state.

    Args:
        available_routes (list): A list of RouteState instances.
    """
    def __init__(self, available_routes):
        if not all(isinstance(r, RouteState) for r in available_routes):
            raise ValueError('available_routes must be comprised of RouteState objects only.')

        self.available_routes = available_routes
        self.ignored_routes = list()
        self.refunded_routes = list()
        self.canceled_routes = list()
