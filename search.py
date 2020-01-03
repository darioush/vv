import json
import typing

from collections import defaultdict
from datetime import datetime
from dateutil.parser import parse 

from cache import get_quotes


class Leg:
    def __init__(self, data, quote, direct, is_inbound):
        self.origin = places[data.get('OriginId')]
        self.dest = places[data.get('DestinationId')]
        self.departure = (parse(data.get('DepartureDate')).date() - datetime(2020, 2, 10).date()).days
        self.quote = quote
        self.direct = direct
        self.is_inbound = is_inbound

    def __str__(self):
        direct = '>>' if self.direct else '->'
        direction = '<' if self.is_inbound else '>'
        if self.is_inbound:
            return f'<({self.departure}) {self.origin} {direct} {self.dest}'
        return f'${self.quote.price} {(self.departure)} {self.origin} {direct} {self.dest}'

    def __repr__(self):
        return str(self)


class Quote:
    def __init__(self, data):
        self.id = data.get('QuoteId')
        self.price = data.get('MinPrice')
        self.direct = data.get('Direct')
        self.data = data
        self.legs = []
        self.legs.append(Leg(data.get('OutboundLeg', {}), self, self.direct, is_inbound=False))
        if 'InboundLeg' in data:
            self.legs.append(Leg(data.get('InboundLeg', {}), self, self.direct, is_inbound=True))

    def __str__(self):
        legs_str = ', '.join(map(str, self.legs))
        return f'{self.id} {legs_str} ${self.price}'

    def __repr__(self):
        return str(self)


universe = set(['SEA', 'LAX', 'MEX', 'SFO', 'EZE', 'YVR', 'GDL', 'GRU', 'SCL', 'UIO', 'BZE', 'LIM'])
max_stay = {
    'SEA': 10,
    'LAX': 2,
    'SFO': 2,
    'YVR': 2,
}
max_trip = 90


places = {}
quotes = {}
edges = defaultdict(list)
wander_map = {}
INF = 10000
MAX_TRIP = 12

point = (0, 'SEA')
parents = {}
distance = {point: 0}
visited = set()
working = [point]

def wander(orig: str, dest: str, outbound: str, inbound: str):
    data = json.loads(get_quotes(orig, dest, outbound, inbound))
    for place in data['Places']:
        places[place['PlaceId']] = place['IataCode']
    for q_data in data['Quotes']:
        q = Quote(q_data)
        for l in q.legs:
            edges[(l.departure, l.origin)].append(((l.departure + 1, l.dest), l))
    print(f'wander {orig}->{dest}:')


def get_parents(point: typing.Tuple[int, str]) -> typing.List[Leg]:
    if point not in parents:
        return []
    pp, pl = parents[point]
    return [pl] + get_parents(pp)


def wander_point(point: typing.Tuple[int, str]):
    departure, orig = point
    for city in universe:
        if city == orig:
            continue
        if (orig, city) not in wander_map:
            wander(orig, city, 'anytime', '')
            wander(orig, city, 'anytime', 'anytime')
            wander_map[(orig, city)] = 1

    parent_legs = get_parents(point)
    if len(parent_legs) > MAX_TRIP:
        return

    for (d, o), vs in edges.items():
        for (next_pos, l) in vs:
            if o != orig or d < departure:
                continue
            if next_pos in visited:
                continue
            if next_pos[0] > max_trip or orig in max_stay and next_pos[0] - departure > max_stay[orig]:
                continue

            if l.is_inbound and l.quote not in set(p.quote for p in parent_legs):
                continue
            price = 0 if l.is_inbound else l.quote.price
            relaxed = distance[point] + price
            if relaxed > INF:
                continue

            if next_pos not in distance or distance[next_pos] > relaxed:
                distance[next_pos] = relaxed
                parents[next_pos] = (point, l)
                working.append(next_pos)


def wander_graph() -> None:
    while len(working) > 0:
        print(f'xx {len(working)}')
        point = min(working, key=lambda w: distance[w])
        working.remove(point)
        if point in visited:
            continue
        wander_point(point)
        visited.add(point)

wander_graph()

trs = {d: (v, list(reversed(get_parents((d, c))))) for (d, c), v in distance.items() if c == 'SEA'}
for k, v in sorted(trs.items(), key=lambda i: i[0]):
    print (k, v)

import ipdb
ipdb.set_trace()
print('boo')
