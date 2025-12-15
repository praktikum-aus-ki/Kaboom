import os
import random
import numpy
import pygame

from enum import Enum
from typing import NamedTuple
from PIL import Image
from pygame import Surface

DISPLAY_SCALE = 4

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
    BUCKET_SPEED_X: int = 5  # in px
    BUCKET_X_OFFSET: int = 40  # in px
    BOMB_FUSE_STATES: int = 3  # bomb fuse animations count
    BOMB_EXPLODE_STATES: int = 11  # bomb animations count 4 + 4 + 3
    BOMB_BUCKET_EXPLODE_STATES: int = 12  # bomb animations count 4 + 4 + 4
    BOMB_SPAWN_HELP_VALUE_Y: int = 20
    BOMB_SIZE: tuple[int, int] = (5, 12)
    BACKGROUND_STATES: int = 32  # background flickers 16 times 2 frames each
    DEFAULT_STATE: int = -1
    MAXIMUM_SCORE: int = 999_999
    BOMBS_COUNT_GROUPS: tuple[int,int,int,int,int,int,int,int] = (10, 20, 30, 40, 50, 75, 100, 150) # bombs count
    MAD_BOMBER_SPEED_GROUPS: tuple[int,int,int,int,int,int,int,int] = (1, 2, 2, 3, 3, 4, 4, 4) # in px
    MAD_BOMBER_RANDOMNESS_NUMBERS: tuple[int, int, int, int, int, int, int, int] = (1, 1, 2, 2, 3, 3, 4, 4) # just numbers
    BOMB_SPEED_GROUPS: tuple[int,int,int,int,int,int,int,int] = (1, 1, 2, 2, 3, 3, 3, 4) # in px
    BOMB_INTERVAL_PX_GROUPS: tuple[int,int,int,int,int,int,int,int] = (36, 18, 18, 10, 12, 6, 6, 3) # in frames
    BACKGROUND_SIZE: tuple[int, int] = (160, 210)
    CUR_BACKGROUND_TOP: tuple[int, int] = (160, 210)
    BACKGROUND_TOP_SIZE: tuple[int, int] = (144, 40)
    BACKGROUND_TOP_POS: tuple[int, int] = (8, 7)
    CUR_BACKGROUND_BOTTOM: tuple[int, int] = (144, 142)
    BACKGROUND_BOTTOM_SIZE: tuple[int, int] = (144, 142)
    BACKGROUND_BOTTOM_POS: tuple[int, int] = (8, 47)
    BUCKET_SIZE: tuple[int, int] = (14, 8)
    BOTTOM_EDGE_Y: int = 189
    MAD_BOMBER_SIZE: tuple[int, int] = (7, 30)
    MAD_BOMBER_POS_X: int = 22
    MAD_BOMBER_POS_Y: int = 19
    BUCKET_THREE_POS_X: int = 73
    BUCKET_THREE_POS_Y: int = 180
    BUCKET_TWO_POS_X: int = 73
    BUCKET_TWO_POS_Y: int = 164
    BUCKET_ONE_POS_X: int = 73
    BUCKET_ONE_POS_Y: int = 148
    TOPLEFT_ALLOWED_POS_X: int = 18
    TOPLEFT_ALLOWED_POS_Y: int = 128


# Agent's observation
class KaboomObservation(NamedTuple):
    mad_bomber_pos: tuple[int, int]
    buckets_pos: list[tuple[int, int]]
    bombs: list[tuple[
        tuple[int, int], int, int, int, int, int]]  # EntityPosition, bomb_fuse_anim_state, bomb_type, explode_state, explode_bucket_state, on_bucket_index
    score: int
    lives: int


# Current game state
class KaboomState(NamedTuple):
    mad_bomber_pos_x: int
    mad_bomber_pos_y: int
    mad_bomber_going_left: bool
    mad_bomber_motion_counter: int
    bombs_states: list[tuple[
        tuple[int, int], int, int, int, int, int]]  # x, y, bomb_fuse_anim_state, bomb_type, explode_state, explode_bucket_state, on_bucket_index
    buckets_pos: list[tuple[int, int]]  # x, y
    buckets_moving_state: int
    buckets_jitter_state: int
    buckets_wereMovingRight: bool
    score: int
    lives: int
    level: int
    frames_counter: int
    bombs_dropped: int
    bombs_falling_and_exploding: bool
    bombs_exploding: bool
    background_flickering: bool
    background_state: int
    level_success: bool
    level_finished: bool

class KaboomSharedInformation:
    cur_background_top: Surface = None
    cur_background_bottom: Surface = None


def _get_observation(state: KaboomState):
    obs = KaboomObservation(
        mad_bomber_pos=(
            state.mad_bomber_pos_x,
            state.mad_bomber_pos_y
        ),
        score=state.score,
        lives=state.lives,
        buckets_pos=[(pos[0], pos[1]) for pos in state.buckets_pos],
        bombs=state.bombs_states,
    )
    return obs


def _reset(consts: KaboomConstants):
    consts = consts or KaboomConstants()
    state = KaboomState(
        mad_bomber_pos_x=consts.MAD_BOMBER_POS_X,
        mad_bomber_pos_y=consts.MAD_BOMBER_POS_Y,
        mad_bomber_going_left=False,
        mad_bomber_motion_counter=0,
        bombs_states=[],
        buckets_pos=[(consts.BUCKET_THREE_POS_X, consts.BUCKET_THREE_POS_Y),(consts.BUCKET_TWO_POS_X, consts.BUCKET_TWO_POS_Y),(consts.BUCKET_ONE_POS_X, consts.BUCKET_ONE_POS_Y)],
        buckets_jitter_state=consts.DEFAULT_STATE,
        buckets_moving_state=consts.DEFAULT_STATE,
        buckets_wereMovingRight=False,
        score=0,
        lives=3,
        level=1,
        bombs_dropped=0,
        frames_counter=0,
        bombs_falling_and_exploding=True,
        bombs_exploding=False,
        background_flickering=False,
        background_state=consts.DEFAULT_STATE,
        level_finished = False,
        level_success = False
    )
    return state


class Action(Enum):
    LEFT = 1
    RIGHT = 2
    NONE = 3

def _get_group_index(level: int):
    return max(1, min(8, level)) - 1

def _step(state: KaboomState, consts: KaboomConstants, action: Action) -> tuple[
    KaboomState, KaboomObservation]:
    if state.lives == 0:
        return state, _get_observation(state)

    if state.score >= consts.MAXIMUM_SCORE:
        return state, _get_observation(state)

    # Update buckets positions
    buckets_wereMovingRight = state.buckets_wereMovingRight
    frames_counter = state.frames_counter
    buckets_pos = state.buckets_pos
    buckets_jitter_state = state.buckets_jitter_state
    buckets_moving_state = state.buckets_moving_state
    if not state.bombs_exploding:
        new_x: int

        # Input + stickiness
        if action in [Action.LEFT, Action.RIGHT]:
            if buckets_moving_state == consts.DEFAULT_STATE:
                buckets_moving_state = 1
            else:
                buckets_moving_state += 1

            if buckets_moving_state > 5:
                buckets_moving_state = 5
        else:
            buckets_moving_state -= 1
            if buckets_moving_state < 0:
                buckets_moving_state = consts.DEFAULT_STATE


        if action == Action.LEFT:
            buckets_wereMovingRight = False
        elif action == Action.RIGHT:
            buckets_wereMovingRight = True


        cur_speed: int
        if buckets_moving_state == consts.DEFAULT_STATE:
            cur_speed = 0
        else:
            cur_speed = int((consts.BUCKET_SPEED_X * 1) * (buckets_moving_state / 5))
            if not buckets_wereMovingRight:
                cur_speed = -cur_speed


        if buckets_wereMovingRight:
            new_x = min(consts.TOPLEFT_ALLOWED_POS_Y, buckets_pos[0][0] + cur_speed)
        else:
            new_x = max(consts.TOPLEFT_ALLOWED_POS_X, buckets_pos[0][0] + cur_speed)


        # bucket jittering
        if buckets_jitter_state == consts.DEFAULT_STATE:
            if frames_counter % 100 == 0:
                if random.randint(1, 3) == 3:
                    buckets_jitter_state = 0
        else:
            if frames_counter % 2 == 0:
                if buckets_jitter_state != consts.DEFAULT_STATE:
                    if buckets_jitter_state in [0, 1, 8, 9, 16, 17]:
                        new_x -= 1
                    elif buckets_jitter_state in [2, 3, 10, 11, 18, 19]:
                        new_x += 1
                buckets_jitter_state += 1
            if buckets_jitter_state == 29:
                buckets_jitter_state = consts.DEFAULT_STATE


        # update buckets pos
        new_bucket_pos = []
        for i in range(len(buckets_pos)):
            new_bucket_pos.append((new_x, buckets_pos[i][1]))
        buckets_pos = new_bucket_pos


    # Update bombs
    bomb_to_remove = None
    other_bomb_exploding: bool = False

    score = state.score
    lives = state.lives
    bombs_should_explode: bool = state.bombs_exploding
    level_finished: bool = state.level_finished
    level_success = state.level_success
    bombs_falling_and_exploding = state.bombs_falling_and_exploding
    bombs_dropped = state.bombs_dropped
    level = state.level
    bombs = state.bombs_states
    if bombs_falling_and_exploding:
        for i in range(len(bombs)):
            bomb_new_position = bombs[i][0]
            new_fuse_anim = bombs[i][1]

            # Check for explosion if bottom is reached
            if (bombs[i][0][1] + consts.BOMB_SIZE[
                1]) >= consts.BOTTOM_EDGE_Y:
                bombs_should_explode = True
                level_finished = True
                level_success = False

            bomb_explode_state: int = consts.DEFAULT_STATE
            if bombs_should_explode:
                if not other_bomb_exploding:
                    bomb_explode_state = bombs[i][3] + 1
                other_bomb_exploding = True


            # Check for explosion if bucket is reached
            bucket_index = bombs[i][5]
            bomb_bucket_explode_state = bombs[i][4]
            if bomb_bucket_explode_state == consts.DEFAULT_STATE:
                bucket_index = 0  # 2 = the top-most
                for bucket in state.buckets_pos:
                    if ((bombs[i][0][1] + consts.BOMB_SIZE[1]) >= bucket[1]
                            and (bombs[i][0][0] + consts.BOMB_SIZE[0]) >= bucket[0]
                            and bombs[i][0][0] <= bucket[0] + consts.BUCKET_SIZE[0]):
                        score += level
                        bomb_bucket_explode_state = 0
                        break
                    bucket_index += 1

            if bomb_bucket_explode_state != consts.DEFAULT_STATE:
                bomb_bucket_explode_state += 1
                bomb_new_position = bombs[i][0]
                new_fuse_anim = bombs[i][1]


            # Update the state of the current bomb
            if not bombs_should_explode and bomb_bucket_explode_state == consts.DEFAULT_STATE:
                bomb_new_position = (
                    bombs[i][0][0],
                    bombs[i][0][1] + 1 * consts.BOMB_SPEED_GROUPS[_get_group_index(level)]
                )
                new_fuse_anim = random.randint(0, consts.BOMB_FUSE_STATES - 1)
                bomb_explode_state = consts.DEFAULT_STATE
                bomb_bucket_explode_state = consts.DEFAULT_STATE
                bucket_index = bombs[i][5]

            bombs[i] = (bomb_new_position, new_fuse_anim, bombs[i][2], bomb_explode_state,
                            bomb_bucket_explode_state, bucket_index)

            # Mark the bomb to be removed
            if bomb_explode_state >= consts.BOMB_EXPLODE_STATES or bomb_bucket_explode_state >= consts.BOMB_BUCKET_EXPLODE_STATES:
                bomb_to_remove = bombs[i]

        # Dropping new bombs
        if bombs_dropped < consts.BOMBS_COUNT_GROUPS[_get_group_index(level)]:
            if not level_finished:
                if frames_counter % consts.BOMB_INTERVAL_PX_GROUPS[_get_group_index(level)] == 0:
                    bombs.append(
                        ((state.mad_bomber_pos_x + 1,state.mad_bomber_pos_y + consts.BOMB_SPAWN_HELP_VALUE_Y),
                         0, random.randint(0, 1), consts.DEFAULT_STATE, consts.DEFAULT_STATE, consts.DEFAULT_STATE))
                    bombs_dropped += 1
        elif len(bombs) == 0:
                level_finished = True
                level_success = True


    if bomb_to_remove is not None:
        bombs.remove(bomb_to_remove)

    # Background state
    background_state = state.background_state
    background_flickering = state.background_flickering
    if bombs_should_explode and len(bombs) == 0:
        bombs_should_explode = False
        background_flickering = True
        bombs_dropped = 0

    if level_finished:
        if not level_success and background_flickering:
            background_state += 1
            if background_state >= consts.BACKGROUND_STATES:
                bombs_dropped = 0
                bombs_falling_and_exploding = True
                level_finished = False
                level_success = False
                background_flickering = False
                background_state = consts.DEFAULT_STATE
                lives -= 1
                buckets_pos.remove(buckets_pos[0])
                if level > 1:
                    level -= 1
        elif level_success and len(bombs) == 0:
            bombs_dropped = 0
            bombs_falling_and_exploding = True
            level_finished = False
            level_success = False
            level = state.level + 1

    # Update mad bomber
    mad_bomber_motion_counter = state.mad_bomber_motion_counter
    mad_bomber_pos_x = state.mad_bomber_pos_x
    mad_bomber_going_left = state.mad_bomber_going_left
    if bombs_dropped < consts.BOMBS_COUNT_GROUPS[_get_group_index(level)] and not level_finished:
        if mad_bomber_motion_counter != 0:
            if mad_bomber_going_left:
                mad_bomber_pos_x -= consts.MAD_BOMBER_SPEED_GROUPS[_get_group_index(level)] * 1
            else:
                mad_bomber_pos_x += consts.MAD_BOMBER_SPEED_GROUPS[_get_group_index(level)] * 1

        if mad_bomber_motion_counter // 18 == 1:
            mad_bomber_motion_counter = 0
            mad_bomber_going_left = bool(random.randint(0, 1))

        if mad_bomber_pos_x >= consts.TOPLEFT_ALLOWED_POS_Y:
            mad_bomber_going_left = True
        elif mad_bomber_pos_x <= consts.TOPLEFT_ALLOWED_POS_X:
            mad_bomber_going_left = False

        mad_bomber_motion_counter += consts.MAD_BOMBER_RANDOMNESS_NUMBERS[_get_group_index(level)]


    frames_counter += 1
    lives = len(state.buckets_pos)

    # Update state and obs
    state = KaboomState(
        mad_bomber_pos_x=mad_bomber_pos_x,
        mad_bomber_pos_y=state.mad_bomber_pos_y,
        mad_bomber_going_left=mad_bomber_going_left,
        mad_bomber_motion_counter=mad_bomber_motion_counter,
        bombs_states=bombs,
        buckets_pos=buckets_pos,
        buckets_jitter_state=buckets_jitter_state,
        buckets_moving_state=buckets_moving_state,
        buckets_wereMovingRight=buckets_wereMovingRight,
        score=score,
        lives=lives,
        level=level,
        frames_counter=frames_counter,
        bombs_dropped=bombs_dropped,
        bombs_falling_and_exploding=bombs_falling_and_exploding,
        bombs_exploding=bombs_should_explode,
        background_flickering=background_flickering,
        background_state=background_state,
        level_finished=level_finished,
        level_success=level_success
    )
    obs = _get_observation(state)

    return state, obs


def _get_random_color(a: int = 10, b: int = 180):
    return random.randint(a, b), random.randint(a, b), random.randint(a, b)


def _render(screen: Surface, state: KaboomState, obs: KaboomObservation, consts: KaboomConstants):
    # Draw background
    background_top = KaboomSharedInformation.cur_background_top
    background_bottom = KaboomSharedInformation.cur_background_bottom
    background_border = KaboomSprites.background[2]

    if state.background_flickering and state.background_state % 2 == 0:
        background_top = background_top.convert_alpha()
        background_top.fill(_get_random_color())
        KaboomSharedInformation.cur_background_top = background_top
        background_bottom = background_bottom.convert_alpha()
        background_bottom.fill(_get_random_color())
        KaboomSharedInformation.cur_background_bottom = background_bottom

    if state.background_flickering and state.background_state == consts.BACKGROUND_STATES - 1:
        if not state.level_finished:
            KaboomSharedInformation.cur_background_top = KaboomSprites.background[0]
            KaboomSharedInformation.cur_background_bottom = KaboomSprites.background[1]
            background_top = KaboomSharedInformation.cur_background_top
            background_bottom = KaboomSharedInformation.cur_background_bottom

    screen.blit(background_border, (0, 0))
    screen.blit(background_top, consts.BACKGROUND_TOP_POS)
    screen.blit(background_bottom, consts.BACKGROUND_BOTTOM_POS)

    # Draw score
    score_pos_x = int(consts.BACKGROUND_TOP_POS[0] + consts.BACKGROUND_TOP_SIZE[
        0] - 60 * 1)
    score_pos_y = int(consts.BACKGROUND_TOP_POS[1] + 1)
    score = str(obs.score)

    for i in reversed(range(len(score))):
        score_pos_x -= 7 * 1
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
            screen.blit(bomb_explode_surface, (relevant_bucket[0], relevant_bucket[1] - bomb_explode_surface.get_size()[1]))
        else:
            # Draw the bomb
            screen.blit(KaboomSprites.bombs[bomb[2]], bomb[0])

            # Draw the bombs fuse
            bomb_fuse = KaboomSprites.bomb_fuse_states[bomb[1]]
            screen.blit(bomb_fuse, (bomb[0][0] + 2 * ((bomb[2] + 1) % 2) * 1,
                                    bomb[0][1] - bomb_fuse.get_size()[1]))

    # Draw buckets
    for bucket_pos in obs.buckets_pos:
        screen.blit(KaboomSprites.bucket,
                    (bucket_pos[0], bucket_pos[1]))


def main():
    # Convert .npy files
    save_npy_as_png()

    # Game constants
    consts = KaboomConstants()

    # Load surfaces and get a scaled screen size
    load_surfaces()
    screen_size = (160, 210)
    scaled_screen_size: tuple[int, int] = scale_size_tuple(screen_size, DISPLAY_SCALE)

    KaboomSharedInformation.cur_background_top = KaboomSprites.background[0]
    KaboomSharedInformation.cur_background_bottom = KaboomSprites.background[1]

    # Load game state
    state = _reset(consts)
    obs = _get_observation(state)

    # Init pygame
    pygame.init()
    clock = pygame.time.Clock()
    screen = pygame.display.set_mode(scaled_screen_size)
    fake_screen = Surface(screen_size)
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
                        ((obs.mad_bomber_pos[0] + 1, obs.mad_bomber_pos[1] + int((KaboomSprites.mad_bomber.get_size()[
                                                              1] - 4 * 1) / 2) + 7 * 1),
                         0, random.randint(0, 1), consts.DEFAULT_STATE, consts.DEFAULT_STATE, consts.DEFAULT_STATE))
                elif event.key == pygame.K_SPACE:
                    if state.level_finished:
                        state = state._replace(bombs_falling=True, level_finished=False)
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
        state, obs = _step(state, consts, action)

        # Render
        _render(fake_screen, state, obs, consts)
        screen.blit(pygame.transform.scale(fake_screen, screen.get_rect().size), (0, 0))
        pygame.display.flip()
        clock.tick(30)

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