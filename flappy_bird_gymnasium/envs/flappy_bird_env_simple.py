#
# Copyright (c) 2020 Gabriel Nogueira (Talendar)
# Copyright (c) 2023 Martin Kubovcik
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ==============================================================================

""" Implementation of a Flappy Bird OpenAI gymnasium environment that yields simple
numerical information about the game's state as observations.
"""

from typing import Dict, Optional, Tuple, Union

import gymnasium
import numpy as np
import pygame

from flappy_bird_gymnasium.envs.game_logic import (
    PIPE_HEIGHT,
    PIPE_WIDTH,
    PLAYER_HEIGHT,
    PLAYER_MAX_VEL_Y,
    PLAYER_WIDTH,
    FlappyBirdLogic,
)
from flappy_bird_gymnasium.envs.renderer import FlappyBirdRenderer


class FlappyBirdEnvSimple(gymnasium.Env):
    """Flappy Bird Gymnasium environment that yields simple observations.

    The observations yielded by this environment are simple numerical
    information about the game's state. Specifically, the observations are:

        * Horizontal distance to the next pipe;
        * Difference between the player's y position and the next hole's y
          position.

    The reward received by the agent in each step is equal to the score obtained
    by the agent in that step. A score point is obtained every time the bird
    passes a pipe.

    Args:
        screen_size (Tuple[int, int]): The screen's width and height.
        normalize_obs (bool): If `True`, the observations will be normalized
            before being returned.
        pipe_gap (int): Space between a lower and an upper pipe.
        bird_color (str): Color of the flappy bird. The currently available
            colors are "yellow", "blue" and "red".
        pipe_color (str): Color of the pipes. The currently available colors are
            "green" and "red".
        background (Optional[str]): Type of background image. The currently
            available types are "day" and "night". If `None`, no background will
            be drawn.
    """

    metadata = {"render_modes": ["human"], "render_fps": 30}

    def __init__(
        self,
        screen_size: Tuple[int, int] = (288, 512),
        audio_on: bool = True,
        normalize_obs: bool = True,
        pipe_gap: int = 100,
        bird_color: str = "yellow",
        pipe_color: str = "green",
        background: Optional[str] = "day",
    ) -> None:
        self.action_space = gymnasium.spaces.Discrete(2)
        self.observation_space = gymnasium.spaces.Box(
            -np.inf, np.inf, shape=(2,), dtype=np.float64
        )
        self._screen_size = screen_size
        self._normalize_obs = normalize_obs
        self._pipe_gap = pipe_gap
        self._audio_on = audio_on

        self._game = None
        self._renderer = None

        self._bird_color = bird_color
        self._pipe_color = pipe_color
        self._bg_type = background

    def _get_observation(self):
        up_pipe = low_pipe = None
        h_dist = 0
        for up_pipe, low_pipe in zip(self._game.upper_pipes,
                                     self._game.lower_pipes):
            h_dist = (low_pipe["x"] + PIPE_WIDTH / 2
                      - (self._game.player_x - PLAYER_WIDTH / 2))
            h_dist += 3  # extra distance to compensate for the buggy hit-box
            if h_dist >= 0:
                break

        upper_pipe_y = up_pipe["y"] + PIPE_HEIGHT
        lower_pipe_y = low_pipe["y"]
        player_y = self._game.player_y

        v_dist = (upper_pipe_y + lower_pipe_y) / 2 - (player_y
                                                      + PLAYER_HEIGHT/2)

        if self._normalize_obs:
            h_dist /= self._screen_size[0]
            v_dist /= self._screen_size[1]

        return np.array([
            h_dist,
            v_dist,
        ])

    def step(
        self,
        action: Union[FlappyBirdLogic.Actions, int],
    ) -> Tuple[np.ndarray, float, bool, Dict]:
        """Given an action, updates the game state.

        Args:
            action (Union[FlappyBirdLogic.Actions, int]): The action taken by
                the agent. Zero (0) means "do nothing" and one (1) means "flap".

        Returns:
            A tuple containing, respectively:

                * an observation (horizontal distance to the next pipe
                  difference between the player's y position and the next hole's
                  y position)
                * a reward (alive = +0.1, pipe = +1.0, dead = -1.0)
                * a status report (`True` if the game is over and `False`
                  otherwise)
                * an info dictionary
        """
        reward, alive = self._game.update_state(action)
        obs = self._get_observation()
        done = not alive
        info = {"score": self._game.score}

        return obs, reward, done, False, info

    def reset(self, seed=None, options=None):
        """Resets the environment (starts a new game)."""
        super().reset(seed=seed)

        self._game = FlappyBirdLogic(
            np_random=self.np_random,
            screen_size=self._screen_size,
            pipe_gap_size=self._pipe_gap,
        )
        if self._renderer is not None:
            self._renderer.game = self._game

        info = {"score": self._game.score}
        return self._get_observation(), info

    def set_color(self, color):
        if self._renderer is not None:
            self._renderer.set_color(color)

    def render(self) -> None:
        """Renders the next frame."""
        if self._renderer is None:
            self._renderer = FlappyBirdRenderer(
                screen_size=self._screen_size,
                audio_on=self._audio_on,
                bird_color=self._bird_color,
                pipe_color=self._pipe_color,
                background=self._bg_type,
            )
            self._renderer.game = self._game
            self._renderer.make_display()

        self._renderer.draw_surface(show_score=True)
        self._renderer.update_display()

    def close(self):
        """Closes the environment."""
        if self._renderer is not None:
            pygame.display.quit()
            pygame.quit()
            self._renderer = None
        super().close()
