""" MIT License

Copyright (c) 2019 Mehmet Kerem Turkcan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE. """

""" MIT License

Copyright (c) 2017 Hannes Karppila

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE. """

import sc2
from sc2 import Race
from sc2.player import Bot

from sc2.units import Units
from sc2.unit import Unit
from sc2.position import Point2, Point3

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.buff_id import BuffId
from sc2.ids.ability_id import AbilityId

from typing import List, Dict, Set, Tuple, Any, Optional, Union # mypy type checking
from random import *
"""
To play an arcade map, you need to download the map first.

Open the StarCraft2 Map Editor through the Battle.net launcher, in the top left go to
File -> Open -> (Tab) Blizzard -> Log in -> with "Source: Map/Mod Name" search for your desired map, in this example "Marine Split Challenge-LOTV" map created by printf
Hit "Ok" and confirm the download. Now that the map is opened, go to "File -> Save as" to store it on your hard drive.
Now load the arcade map by entering your map name below in
sc2.maps.get("YOURMAPNAME") without the .SC2Map extension


Map info:
You start with 30 marines, level N has 15+N speed banelings on creep

Type in game "sling" to activate zergling+baneling combo
Type in game "stim" to activate stimpack


Reaches level 30 in ~8 ingame minutes. Hyperparameters have not been tuned.
"""

class MarineSplitChallenge(sc2.BotAI):
    async def on_step(self, iteration):
        if iteration == 0:
            await self.on_first_iteration()

        actions = []

        # do marine micro vs zerglings
        for unit in self.units(UnitTypeId.MARINE):

            if self.known_enemy_units:
                mode = 'attack'
                if unit.weapon_cooldown > self._client.game_step / 2:
                    mode = 'runaway'
                enemies_in_range = self.known_enemy_units.filter(lambda u: unit.target_in_range(u))
                # Running away from banelings behavior
                filtered_enemies_in_range = enemies_in_range.of_type(UnitTypeId.BANELING)
                if filtered_enemies_in_range:
                    closest_enemy = filtered_enemies_in_range.closest_to(unit)
                    if unit.distance_to(closest_enemy)<0.2*unit.ground_range:
                        mode = 'runaway'
                friends_in_range = self.units(UnitTypeId.MARINE).filter(lambda u: unit.target_in_range(u, -0.5))
                # Clustering behavior
                if len(friends_in_range) > 2. * len(enemies_in_range) and len(friends_in_range)>4:
                    if random()<0.5:
                        mode = 'runaway'
                # attack (or move towards) zerglings / banelings
                if mode == 'attack':
                    enemies_in_range = self.known_enemy_units.filter(lambda u: unit.target_in_range(u))
                    

                    # attack lowest hp enemy if any enemy is in range
                    if enemies_in_range:
                        # Use stimpack
                        if self.already_pending_upgrade(UpgradeId.STIMPACK) == 1 and not unit.has_buff(BuffId.STIMPACK) and unit.health > 10:
                            actions.append(unit(AbilityId.EFFECT_STIM))


                        # attack baneling first
                        filtered_enemies_in_range = enemies_in_range.of_type(UnitTypeId.BANELING)

                        if not filtered_enemies_in_range:
                            filtered_enemies_in_range = enemies_in_range.of_type(UnitTypeId.ZERGLING)
                        # attack lowest hp unit
                        lowest_hp_enemy_in_range = min(filtered_enemies_in_range, key=lambda u: u.health)
                        actions.append(unit.attack(lowest_hp_enemy_in_range))

                    # no enemy is in attack-range, so give attack command to closest instead
                    else:
                        closest_enemy = self.known_enemy_units.closest_to(unit)
                        actions.append(unit.attack(closest_enemy))


                # move away from zergling / banelings
                else:
                    stutter_step_positions = self.position_around_unit(unit, distance=4)

                    # filter in pathing grid
                    stutter_step_positions = {p for p in stutter_step_positions if self.in_pathing_grid(p)}

                    # find position furthest away from enemies and closest to unit
                    enemies_in_range = self.known_enemy_units.filter(lambda u: unit.target_in_range(u, -0.5))
                    friends_in_range = self.units(UnitTypeId.MARINE).filter(lambda u: unit.target_in_range(u, -0.5))
                    all_in_range = enemies_in_range | friends_in_range

                    if stutter_step_positions and all_in_range:
                        retreat_position = max(stutter_step_positions, key=lambda x: x.distance_to(all_in_range.center) - x.distance_to(unit))
                        actions.append(unit.move(retreat_position))

                    else:
                        print("No retreat positions detected for unit {} at {}.".format(unit, unit.position.rounded))

        await self.do_actions(actions)



    async def on_first_iteration(self):
        await self.chat_send("Edit this message for automatic chat commands.")
        self._client.game_step = 2 # do actions every X frames instead of every 8th



    def position_around_unit(self, pos: Union[Unit, Point2, Point3], distance: int=1, step_size: int=1, exclude_out_of_bounds: bool=True):
        pos = pos.position.to2.rounded
        positions = {pos.offset(Point2((x, y)))
                     for x in range(-distance, distance+1, step_size)
                     for y in range(-distance, distance+1, step_size)
                     if (x, y) != (0, 0)}
        # filter positions outside map size
        if exclude_out_of_bounds:
            positions = {p for p in positions if 0 <= p[0] < self._game_info.pathing_grid.width and 0 <= p[1] < self._game_info.pathing_grid.height}
        return positions


def main():
    sc2.run_game(sc2.maps.get("Marine Split Challenge"), [
        Bot(Race.Terran, MarineSplitChallenge()),
    ], realtime=False, save_replay_as="Example.SC2Replay")

if __name__ == '__main__':
    main()
