import math
import os
import random
from enum import Enum
from typing import NamedTuple

import numpy
import pygame
from PIL import Image
from pygame import Surface


# Entity class
class EntityPosition(NamedTuple):
    x: int
    y: int


# Game sprites
class KaboomSprites(NamedTuple):
    background: list[Surface]  # top, bottom, border
    mad_bomber: Surface
    bucket: Surface
    bombs: list[Surface]
    bomb_fuse_states: list[Surface]
    bomb_explode_states: list[Surface]
    bomb_bucket_explode_states: list[Surface]
    scores: list[Surface]


# Game contents
class KaboomConstants(NamedTuple):
    MAD_BOMBER_SPEED_X: int = 1  # in px
    BOMB_SPEED_Y: int = 1  # in px
    BUCKET_SPEED_X: int = 5  # in px
    BUCKET_X_OFFSET: int = 40  # in px
    DISPLAY_SCALE: int = 4
    BOMB_FUSE_STATES: int = 3  # bomb fuse animations count
    BOMB_EXPLODE_STATES: int = 11  # bomb animations count 4 + 4 + 3
    BOMB_BUCKET_EXPLODE_STATES: int = 12  # bomb animations count 4 + 4 + 4
    BACKGROUND_STATES: int = 32  # background flickers 16 times 2 frames each
    DEFAULT_STATE: int = -1
    # INITIAL_BOMBER_POS depends on background pos


# Everything you see on the screen
class KaboomObservation(NamedTuple):
    mad_bomber_pos: EntityPosition
    buckets_pos: list[EntityPosition]
    bombs: list[tuple[
        EntityPosition, int, int, int, int, int]]  # EntityPosition, bomb_fuse_anim_state, bomb_type, explode_state, explode_bucket_state, on_bucket_index
    score: int
    lives: int
    bombs_falling: bool
    bombs_exploding: bool
    background_flickering: bool
    background_state: int


# Current game state
class KaboomState(NamedTuple):
    mad_bomber_pos_x: int
    mad_bomber_pos_y: int
    bombs_states: list[tuple[
        int, int, int, int, int, int, int]]  # x, y, bomb_fuse_anim_state, bomb_type, explode_state, explode_bucket_state, on_bucket_index
    buckets_pos: list[tuple[int, int]]  # x, y
    score: int
    lives: int
    bombs_falling: bool
    bombs_exploding: bool
    background_flickering: bool
    background_state: int


class KaboomSharedInformation:
    scaled_screen_size: tuple[int, int] = (0, 0)
    background_size: tuple[int, int] = (0, 0)
    background_top_size: tuple[int, int] = (0, 0)
    background_top_pos: tuple[int, int] = (0, 0)
    background_bottom_size: tuple[int, int] = (0, 0)
    background_bottom_pos: tuple[int, int] = (0, 0)
    bucket_size: tuple[int, int] = (0, 0)
    bottom_edge_y: int = 0


def _get_observation(state: KaboomState, consts: KaboomConstants = None):
    consts = consts or KaboomConstants()
    obs = KaboomObservation(
        mad_bomber_pos=EntityPosition(
            x=state.mad_bomber_pos_x,
            y=state.mad_bomber_pos_y
        ),
        score=state.score,
        lives=state.lives,
        bombs_falling=state.bombs_falling,
        buckets_pos=[EntityPosition(x=pos[0], y=pos[1]) for pos in state.buckets_pos],
        bombs=[
            (EntityPosition(
                x=state.mad_bomber_pos_x + consts.DISPLAY_SCALE,
                y=state.mad_bomber_pos_y + int(
                    (KaboomSprites.mad_bomber.get_size()[
                         1] - 4 * consts.DISPLAY_SCALE) / 2) + 7 * consts.DISPLAY_SCALE),
             0, 0, consts.DEFAULT_STATE, consts.DEFAULT_STATE, consts.DEFAULT_STATE)
        ],
        bombs_exploding=False,
        background_flickering=False,
        background_state=consts.DEFAULT_STATE
    )
    return obs


def _reset(consts: KaboomConstants):
    consts = consts or KaboomConstants()
    mad_bomber_pos_x = int(KaboomSharedInformation.background_size[0] / 20) + int(
        KaboomSharedInformation.background_top_size[0] * 0.1)
    mad_bomber_pos_y = int(KaboomSharedInformation.background_top_size[1] * 0.3) + int(
        KaboomSharedInformation.background_size[1] / 30)
    state = KaboomState(
        mad_bomber_pos_x=mad_bomber_pos_x,
        mad_bomber_pos_y=mad_bomber_pos_y,
        bombs_states=[
            # x
            (mad_bomber_pos_x + consts.DISPLAY_SCALE,
             # y
             mad_bomber_pos_y + int(
                 (KaboomSprites.mad_bomber.get_size()[1] - 4 * consts.DISPLAY_SCALE) / 2) + 7 * consts.DISPLAY_SCALE,
             # bomb_fuse_anim_state
             0, 0, consts.DEFAULT_STATE, consts.DEFAULT_STATE, consts.DEFAULT_STATE)
        ],
        buckets_pos=[
            (math.ceil(
                KaboomSharedInformation.background_size[0] / 20 + KaboomSharedInformation.background_top_size[
                    0] * 0.451),
             KaboomSharedInformation.background_top_size[1] + KaboomSharedInformation.background_bottom_size[
                 1] + int(
                 KaboomSharedInformation.background_size[1] / 30) - consts.DISPLAY_SCALE -
             KaboomSharedInformation.bucket_size[1]
            ),

            (math.ceil(
                KaboomSharedInformation.background_size[0] / 20 + KaboomSharedInformation.background_top_size[
                    0] * 0.451),
             KaboomSharedInformation.background_top_size[1] + KaboomSharedInformation.background_bottom_size[
                 1] + int(
                 KaboomSharedInformation.background_size[1] / 30) - consts.DISPLAY_SCALE -
             KaboomSharedInformation.bucket_size[1] * 3
            ),

            (math.ceil(
                KaboomSharedInformation.background_size[0] / 20 + KaboomSharedInformation.background_top_size[
                    0] * 0.451),
             KaboomSharedInformation.background_top_size[1] + KaboomSharedInformation.background_bottom_size[
                 1] + int(
                 KaboomSharedInformation.background_size[1] / 30) - consts.DISPLAY_SCALE -
             KaboomSharedInformation.bucket_size[1] * 5
            )
        ],
        score=0,
        lives=3,
        bombs_falling=True,
        bombs_exploding=False,
        background_flickering=False,
        background_state=consts.DEFAULT_STATE
    )
    return state


class Action(Enum):
    LEFT = 1
    RIGHT = 2
    NONE = 3


def _step(state: KaboomState, obs: KaboomObservation, consts: KaboomConstants, action: Action) -> tuple[
    KaboomState, KaboomObservation]:
    if len(obs.buckets_pos) == 0:
        print("ERROR")
        pass

    # Update buckets positions
    bucket_pos = obs.buckets_pos
    if not obs.bombs_exploding:
        new_x: int = bucket_pos[0].x
        if action == Action.LEFT:
            new_x = max(KaboomSharedInformation.background_bottom_pos[0] + 10 * consts.DISPLAY_SCALE,
                        bucket_pos[0].x - consts.BUCKET_SPEED_X * consts.DISPLAY_SCALE)
        elif action == Action.RIGHT:
            new_x = min(KaboomSharedInformation.background_bottom_pos[0] + KaboomSharedInformation.background_bottom_size[
                0] - 10 * consts.DISPLAY_SCALE - KaboomSharedInformation.bucket_size[0],
                        bucket_pos[0].x + consts.BUCKET_SPEED_X * consts.DISPLAY_SCALE)
        new_bucket_pos = []
        for i in range(len(bucket_pos)):
            new_bucket_pos.append(EntityPosition(new_x, bucket_pos[i].y))
        bucket_pos = new_bucket_pos


    # Update bombs
    score = obs.score
    lives = obs.lives
    bomb_to_remove = None
    bombs_should_explode: bool = obs.bombs_exploding
    other_bomb_exploding: bool = False
    if state.bombs_falling:
        for i in range(len(obs.bombs)):
            bomb_new_position = obs.bombs[i][0]
            new_fuse_anim = obs.bombs[i][1]

            # Check for explosion if bottom is reached
            if (obs.bombs[i][0].y + KaboomSprites.bombs[0].get_size()[
                1]) >= KaboomSharedInformation.bottom_edge_y:
                bombs_should_explode = True


            bomb_explode_state: int = consts.DEFAULT_STATE
            if bombs_should_explode:
                bomb_new_position = obs.bombs[i][0]
                new_fuse_anim = obs.bombs[i][1]
                if not other_bomb_exploding:
                    bomb_explode_state = obs.bombs[i][3] + 1
                other_bomb_exploding = True

            # Check for explosion if bucket is reached
            bucket_index = obs.bombs[i][5]
            bomb_bucket_explode_state = obs.bombs[i][4]
            if bomb_bucket_explode_state == consts.DEFAULT_STATE:
                bucket_index = 0  # 2 = the top-most
                for bucket in obs.buckets_pos:
                    if ((obs.bombs[i][0].y + KaboomSprites.bombs[0].get_size()[1]) >= bucket.y
                            and (obs.bombs[i][0].x + KaboomSprites.bombs[0].get_size()[0]) >= bucket.x
                            and obs.bombs[i][0].x <= bucket.x + KaboomSharedInformation.bucket_size[0]):
                        score += 3 - bucket_index
                        bomb_bucket_explode_state = 0
                        break
                    bucket_index += 1

            if bomb_bucket_explode_state != consts.DEFAULT_STATE:
                bomb_bucket_explode_state += 1
                bomb_new_position = obs.bombs[i][0]
                new_fuse_anim = obs.bombs[i][1]


            # Update the state of the current bomb
            if not bombs_should_explode and bomb_bucket_explode_state == consts.DEFAULT_STATE:
                bomb_new_position = EntityPosition(
                    x=obs.bombs[i][0].x,
                    y=obs.bombs[i][0].y + consts.DISPLAY_SCALE * consts.BOMB_SPEED_Y
                )
                new_fuse_anim = random.randint(0, consts.BOMB_FUSE_STATES - 1)
                bomb_explode_state = consts.DEFAULT_STATE
                bomb_bucket_explode_state = consts.DEFAULT_STATE
                bucket_index = obs.bombs[i][5]

            obs.bombs[i] = (bomb_new_position, new_fuse_anim, obs.bombs[i][2], bomb_explode_state,
                            bomb_bucket_explode_state, bucket_index)

            # Mark the bomb to be removed
            if bomb_explode_state >= consts.BOMB_EXPLODE_STATES or bomb_bucket_explode_state >= consts.BOMB_BUCKET_EXPLODE_STATES:
                bomb_to_remove = obs.bombs[i]

    if bomb_to_remove is not None:
        obs.bombs.remove(bomb_to_remove)

    background_state = obs.background_state
    background_flickering = obs.background_flickering
    if bombs_should_explode and len(obs.bombs) == 0:
        bombs_should_explode = False
        background_flickering = True

    if background_flickering:
        background_state += 1
        if background_state >= consts.BACKGROUND_STATES:
            background_flickering = False
            background_state = consts.DEFAULT_STATE
            lives -= 1
            bucket_pos.remove(bucket_pos[0])

    obs = KaboomObservation(
        mad_bomber_pos=obs.mad_bomber_pos,
        score=score,
        lives=obs.lives,
        bombs_falling=obs.bombs_falling,
        buckets_pos=bucket_pos,
        bombs=obs.bombs,
        bombs_exploding=bombs_should_explode,
        background_flickering=background_flickering,
        background_state=background_state
    )

    # Update state and obs
    state = KaboomState(
        mad_bomber_pos_x=obs.mad_bomber_pos.x,
        mad_bomber_pos_y=obs.mad_bomber_pos.y,
        bombs_states=[(bomb_state[0].x, bomb_state[0].y, bomb_state[1], bomb_state[2], bomb_state[3], bomb_state[4], bomb_state[5]) for
                      bomb_state in obs.bombs],
        buckets_pos=[EntityPosition(x=pos[0], y=pos[1]) for pos in state.buckets_pos],
        score=obs.score,
        lives=obs.lives,
        bombs_falling=obs.bombs_falling,
        bombs_exploding=obs.bombs_exploding,
        background_flickering=obs.background_flickering,
        background_state=obs.background_state
    )
    return state, obs


def _get_random_color(a: int = 10, b: int = 180):
    return random.randint(a, b), random.randint(a, b), random.randint(a, b)


def _render(screen: Surface, obs: KaboomObservation, consts: KaboomConstants):
    # Draw background
    background_top = KaboomSprites.background[0]
    background_bottom = KaboomSprites.background[1]
    background_border = KaboomSprites.background[2]

    if obs.background_flickering and obs.background_state % 2 == 0:
        background_top = background_top.convert_alpha()
        background_top.fill(_get_random_color())
        KaboomSprites.background[0] = background_top
        background_bottom = background_bottom.convert_alpha()
        background_bottom.fill(_get_random_color())
        KaboomSprites.background[1] = background_bottom

    screen.blit(background_border, (0, 0))
    screen.blit(background_top, KaboomSharedInformation.background_top_pos)
    screen.blit(background_bottom, KaboomSharedInformation.background_bottom_pos)

    # Draw score
    score_pos_x = int(KaboomSharedInformation.background_top_pos[0] + KaboomSharedInformation.background_top_size[
        0] - 60 * consts.DISPLAY_SCALE)
    score_pos_y = int(KaboomSharedInformation.background_top_pos[1] + consts.DISPLAY_SCALE)
    score = str(obs.score)

    for i in reversed(range(len(score))):
        score_pos_x -= 7 * consts.DISPLAY_SCALE
        screen.blit(KaboomSprites.scores[int(score[i])], (score_pos_x, score_pos_y))

    # Draw mad bomber
    screen.blit(KaboomSprites.mad_bomber, obs.mad_bomber_pos)

    # Draw bombs
    for i in range(len(obs.bombs)):
        bomb = obs.bombs[i]
        if bomb[3] != consts.DEFAULT_STATE:
            explode_surface_index = int(bomb[3] > 3) + int(bomb[3] > 7)
            bomb_explode_surface = KaboomSprites.bomb_explode_states[explode_surface_index].convert_alpha()
            bomb_explode_surface.fill(_get_random_color(), special_flags=pygame.BLEND_RGBA_MIN)

            screen.blit(bomb_explode_surface, obs.bombs[0][0])
        elif bomb[4] != consts.DEFAULT_STATE:
            explode_surface_index = int(bomb[4] > 3) + int(bomb[4] > 7)
            bomb_explode_surface = KaboomSprites.bomb_bucket_explode_states[explode_surface_index]
            relevant_bucket = obs.buckets_pos[bomb[5]]
            screen.blit(bomb_explode_surface, (relevant_bucket.x, relevant_bucket.y - bomb_explode_surface.get_size()[1]))
        else:
            # Draw the bomb
            screen.blit(KaboomSprites.bombs[bomb[2]], bomb[0])

            # Draw the bombs fuse
            bomb_fuse = KaboomSprites.bomb_fuse_states[bomb[1]]
            screen.blit(bomb_fuse, (bomb[0].x + 2 * ((bomb[2] + 1) % 2) * consts.DISPLAY_SCALE,
                                    bomb[0].y - bomb_fuse.get_size()[1]))

    # Draw buckets
    for bucket_pos in obs.buckets_pos:
        screen.blit(KaboomSprites.bucket,
                    EntityPosition(x=bucket_pos.x,
                                   y=bucket_pos.y))


def main():
    # Convert .npy files
    save_npy_as_png()

    # Game constants
    consts = KaboomConstants()

    # Load surfaces and get a scaled screen size
    load_surfaces()
    scale_surfaces(consts)
    scaled_screen_size: tuple[int, int] = scale_size_tuple((160, 210), consts.DISPLAY_SCALE)

    # Init shared variables
    KaboomSharedInformation.scaled_screen_size = scaled_screen_size
    KaboomSharedInformation.background_size = KaboomSprites.background[2].get_size()
    KaboomSharedInformation.background_top_size = KaboomSprites.background[0].get_size()
    KaboomSharedInformation.background_top_pos = (int(KaboomSharedInformation.background_size[0] / 20),
                                                  int(KaboomSharedInformation.background_size[1] / 30))
    KaboomSharedInformation.background_bottom_size = KaboomSprites.background[1].get_size()
    KaboomSharedInformation.background_bottom_pos = (int(KaboomSharedInformation.background_size[0] / 20), int(
        KaboomSharedInformation.background_top_size[1] + KaboomSharedInformation.background_size[1] / 30))
    KaboomSharedInformation.bucket_size = KaboomSprites.bucket.get_size()
    KaboomSharedInformation.bottom_edge_y = int(KaboomSharedInformation.background_size[1] / 30) + \
                                            KaboomSharedInformation.background_top_size[1] + \
                                            KaboomSharedInformation.background_bottom_size[1]

    # Load game state
    state = _reset(consts)
    obs = _get_observation(state, consts)

    # Init pygame
    pygame.init()
    clock = pygame.time.Clock()
    screen = pygame.display.set_mode(scaled_screen_size)
    running = True

    paused = False
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_w:
                    obs.bombs.append(
                        (EntityPosition(
                            x=obs.mad_bomber_pos.x + consts.DISPLAY_SCALE,
                            y=obs.mad_bomber_pos.y + int((KaboomSprites.mad_bomber.get_size()[
                                                              1] - 4 * consts.DISPLAY_SCALE) / 2) + 7 * consts.DISPLAY_SCALE),
                         0, random.randint(0, 1), consts.DEFAULT_STATE, consts.DEFAULT_STATE, consts.DEFAULT_STATE))

        # Update if a key is pressed (and hold)
        action = Action.NONE
        keys_pressed = pygame.key.get_pressed()
        if keys_pressed[pygame.K_LEFT]:
            action = Action.LEFT
        elif keys_pressed[pygame.K_RIGHT]:
            action = Action.RIGHT
        elif keys_pressed[pygame.K_SPACE]:
            paused = True

        if paused:
            paused = False
            continue

        # Step
        state, obs = _step(state, obs, consts, action)

        # Render
        _render(screen, obs, consts)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


def load_surfaces():
    KaboomSprites.background = [
        pygame.image.load("sprites/background_top.png"),
        pygame.image.load("sprites/background_bottom.png"),
        pygame.image.load("sprites/background_border.png")
    ]
    KaboomSprites.mad_bomber = pygame.image.load("sprites/mad-bomber.png")
    KaboomSprites.bucket = pygame.image.load("sprites/bucket.png")
    KaboomSprites.bombs = [
        pygame.image.load("sprites/bomb1.png"),
        pygame.image.load("sprites/bomb2.png")
    ]
    KaboomSprites.bomb_fuse_states = [
        pygame.image.load("sprites/fuse_anim1.png"),
        pygame.image.load("sprites/fuse_anim2.png"),
        pygame.image.load("sprites/fuse_anim3.png")
    ]
    KaboomSprites.bomb_explode_states = [
        pygame.image.load("sprites/bomb_explode_anim1.png"),
        pygame.image.load("sprites/bomb_explode_anim2.png"),
        pygame.image.load("sprites/bomb_explode_anim3.png")
    ]
    KaboomSprites.bomb_bucket_explode_states = [
        pygame.image.load("sprites/bomb_caught_anim1.png"),
        pygame.image.load("sprites/bomb_caught_anim2.png"),
        pygame.image.load("sprites/bomb_caught_anim3.png")
    ]
    KaboomSprites.scores = [
        pygame.image.load("sprites/score0.png"),
        pygame.image.load("sprites/score1.png"),
        pygame.image.load("sprites/score2.png"),
        pygame.image.load("sprites/score3.png"),
        pygame.image.load("sprites/score4.png"),
        pygame.image.load("sprites/score5.png"),
        pygame.image.load("sprites/score6.png"),
        pygame.image.load("sprites/score7.png"),
        pygame.image.load("sprites/score8.png"),
        pygame.image.load("sprites/score9.png")
    ]


def scale_surfaces(consts: KaboomConstants):
    KaboomSprites.background = [
        _scale_surface(KaboomSprites.background[0], consts.DISPLAY_SCALE),
        _scale_surface(KaboomSprites.background[1], consts.DISPLAY_SCALE),
        _scale_surface(KaboomSprites.background[2], consts.DISPLAY_SCALE)
    ]
    KaboomSprites.mad_bomber = _scale_surface(KaboomSprites.mad_bomber, consts.DISPLAY_SCALE)
    KaboomSprites.bucket = _scale_surface(KaboomSprites.bucket, consts.DISPLAY_SCALE)
    KaboomSprites.bombs = [
        _scale_surface(KaboomSprites.bombs[0], consts.DISPLAY_SCALE),
        _scale_surface(KaboomSprites.bombs[1], consts.DISPLAY_SCALE)
    ]
    KaboomSprites.bomb_fuse_states = [
        _scale_surface(KaboomSprites.bomb_fuse_states[0], consts.DISPLAY_SCALE),
        _scale_surface(KaboomSprites.bomb_fuse_states[1], consts.DISPLAY_SCALE),
        _scale_surface(KaboomSprites.bomb_fuse_states[2], consts.DISPLAY_SCALE)
    ]
    KaboomSprites.bomb_explode_states = [
        _scale_surface(KaboomSprites.bomb_explode_states[0], consts.DISPLAY_SCALE),
        _scale_surface(KaboomSprites.bomb_explode_states[1], consts.DISPLAY_SCALE),
        _scale_surface(KaboomSprites.bomb_explode_states[2], consts.DISPLAY_SCALE)
    ]
    KaboomSprites.bomb_bucket_explode_states = [
        _scale_surface(KaboomSprites.bomb_bucket_explode_states[0], consts.DISPLAY_SCALE),
        _scale_surface(KaboomSprites.bomb_bucket_explode_states[1], consts.DISPLAY_SCALE),
        _scale_surface(KaboomSprites.bomb_bucket_explode_states[2], consts.DISPLAY_SCALE)
    ]
    KaboomSprites.scores = [
        _scale_surface(KaboomSprites.scores[0], consts.DISPLAY_SCALE),
        _scale_surface(KaboomSprites.scores[1], consts.DISPLAY_SCALE),
        _scale_surface(KaboomSprites.scores[2], consts.DISPLAY_SCALE),
        _scale_surface(KaboomSprites.scores[3], consts.DISPLAY_SCALE),
        _scale_surface(KaboomSprites.scores[4], consts.DISPLAY_SCALE),
        _scale_surface(KaboomSprites.scores[5], consts.DISPLAY_SCALE),
        _scale_surface(KaboomSprites.scores[6], consts.DISPLAY_SCALE),
        _scale_surface(KaboomSprites.scores[7], consts.DISPLAY_SCALE),
        _scale_surface(KaboomSprites.scores[8], consts.DISPLAY_SCALE),
        _scale_surface(KaboomSprites.scores[9], consts.DISPLAY_SCALE)
    ]


def _scale_surface(surface: Surface, scale: int):
    size = surface.get_size()
    return pygame.transform.scale(surface, (size[0] * scale, size[1] * scale))


def scale_size_tuple(display_size: tuple[int, int], scale: int) -> tuple[int, int]:
    return scale * display_size[0], scale * display_size[1]


def save_npy_as_png():
    dirname = "sprites"
    dirs = os.listdir(dirname)
    for cur_dir in dirs:
        if not cur_dir.endswith(".npy"):
            continue
        arr = numpy.load(os.path.join(dirname, cur_dir))
        img = Image.fromarray(arr)
        img.save(os.path.join(dirname, cur_dir.replace(".npy", ".png")))


if __name__ == "__main__":
    main()
