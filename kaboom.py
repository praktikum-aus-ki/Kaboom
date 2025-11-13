import math
import os
from typing import NamedTuple

import pygame
import numpy
from PIL import Image
from pygame import Surface

class Sprites:
    background: list[Surface]
    mad_bomber: Surface
    bucket: Surface

class EntityPosition(NamedTuple):
    x: int
    y: int

class KaboomConstants:
    DISPLAY_SCALE: int
    MAD_BOMBER_SPEED: int

class KaboomObservation:
    mad_bomber: EntityPosition
    buckets: list[EntityPosition]
    score: int


def main():
    # Convert .npy files
    save_npy_as_png()

    # Load surfaces and get a screen size
    KaboomConstants.DISPLAY_SCALE = 7
    load_surfaces()
    screen_size: tuple[int, int] = scale_size_tuple((160, 210), KaboomConstants.DISPLAY_SCALE)

    # Init pygame
    pygame.init()
    clock = pygame.time.Clock()
    screen = pygame.display.set_mode(screen_size)
    running = True

    # Scale surfaces
    background_top = scale_surface(Sprites.background[0], KaboomConstants.DISPLAY_SCALE)
    background_bottom = scale_surface(Sprites.background[1], KaboomConstants.DISPLAY_SCALE)
    background_border = scale_surface(Sprites.background[2], KaboomConstants.DISPLAY_SCALE)
    mad_bomber = scale_surface(Sprites.mad_bomber, KaboomConstants.DISPLAY_SCALE)
    bucket = scale_surface(Sprites.bucket, KaboomConstants.DISPLAY_SCALE)

    # Initialize observation attributes
    background_size = background_border.get_size()
    background_top_size = background_top.get_size()
    background_bottom_size = background_bottom.get_size()
    KaboomObservation.mad_bomber = EntityPosition(
        x=int(background_size[0] / 20) + int(background_top_size[0] * 0.1),
        y=int(background_top_size[1] * 0.3) + int(background_size[1] / 30)
    )
    KaboomObservation.buckets = [
        EntityPosition(
            x=math.ceil(background_size[0] / 20 + background_top_size[0] * 0.451),
            y=background_top_size[1] + background_bottom_size[1] + int(background_size[1] / 30) - KaboomConstants.DISPLAY_SCALE - bucket.get_size()[1] * 5
        ),
        EntityPosition(
            x=math.ceil(background_size[0] / 20 + background_top_size[0] * 0.451),
            y=background_top_size[1] + background_bottom_size[1] + int(background_size[1] / 30) - KaboomConstants.DISPLAY_SCALE - bucket.get_size()[1] * 3
        ),
        EntityPosition(
            x=math.ceil(background_size[0] / 20 + background_top_size[0] * 0.451),
            y=background_top_size[1] + background_bottom_size[1] + int(background_size[1] / 30) - KaboomConstants.DISPLAY_SCALE - bucket.get_size()[1]
        )
    ]
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Draw surfaces
        screen.blit(background_border, (0,0))
        screen.blit(background_top, (background_size[0] / 20, background_size[1] / 30))
        screen.blit(background_bottom, (background_size[0] / 20, background_top_size[1] + background_size[1] / 30))
        screen.blit(mad_bomber, KaboomObservation.mad_bomber)
        for bucket_position in KaboomObservation.buckets:
            screen.blit(bucket, bucket_position)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

def load_surfaces():
    Sprites.background = [
        pygame.image.load("sprites/background_top.png"),
        pygame.image.load("sprites/background_bottom.png"),
        pygame.image.load("sprites/background_border.png")
    ]
    Sprites.mad_bomber = pygame.image.load("sprites/mad-bomber.png")
    Sprites.bucket = pygame.image.load("sprites/bucket.png")

def scale_surface(surface: Surface, scale: int):
    size = surface.get_size()
    return pygame.transform.scale(surface, (size[0] * scale, size[1] * scale))

def scale_size_tuple(display_size: tuple[int, int], scale: int) -> tuple[int, int]:
    return scale * display_size[0], scale * display_size[1]

def save_npy_as_png():
    dirname = "sprites"
    dirs = os.listdir(dirname)
    for dir in dirs:
        if not dir.endswith(".npy"):
            continue
        arr = numpy.load(os.path.join(dirname, dir))
        img = Image.fromarray(arr)
        img.save(os.path.join(dirname, dir.replace(".npy", ".png")))

if __name__ == "__main__":
    main()
