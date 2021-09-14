# Third-party imports
import numpy as np
import pytest
from matplotlib.colors import ListedColormap
from numpy.testing import assert_array_equal

# Local imports
from plotski.rgb import ImageRGBA
from plotski.utilities import get_random_hex_color


def get_images(n_items):
    return [np.random.randint(0, 255, (10, 10)) for _ in range(n_items)]


def get_colors(n_items):
    return [get_random_hex_color() for _ in range(n_items)]


class TestImageRGBA:
    @staticmethod
    @pytest.mark.parametrize("n_images", (1, 3, 5))
    def test_init_images_hex(n_images):
        images = get_images(n_images)
        image_rgb = ImageRGBA(images)
        assert image_rgb
        assert len(image_rgb._original) == len(image_rgb._images) == len(image_rgb._colors) == n_images

        assert "images=" in repr(image_rgb)

    @staticmethod
    @pytest.mark.parametrize("n_images", (1, 3, 5))
    def test_init_images_rgb(n_images):
        images = get_images(n_images)
        image_rgb = ImageRGBA(images, colors=[[1, 0, 0.7]] * n_images)
        assert image_rgb
        assert len(image_rgb._original) == len(image_rgb._images) == len(image_rgb._colors) == n_images

        assert "images=" in repr(image_rgb)

    @staticmethod
    def test_init_fails():
        with pytest.raises(ValueError):
            _ = ImageRGBA(get_images(1)[0])

        with pytest.raises(ValueError):
            _ = ImageRGBA([np.random.randint(0, 255, (10, 10)), np.random.randint(0, 255, (10, 9))])

    @staticmethod
    @pytest.mark.parametrize("color", ("#FF00FF", (1, 0, 1)))
    def test_init_colors_pass(color):
        _ = ImageRGBA(get_images(1), colors=[color])

    @pytest.mark.parametrize("color", ("FFF000", [1, 0], [1, 0, 0, 0, 1]))
    def test_init_colors_fail(self, color):
        with pytest.raises(ValueError):
            _ = ImageRGBA(get_images(1), colors=[color])

    @staticmethod
    @pytest.mark.parametrize("n_images", (1, 3, 5))
    def test_init_images_with_colors(n_images):
        images, colors = get_images(n_images), get_colors(n_images)
        image_rgb = ImageRGBA(images, colors)
        assert image_rgb
        assert len(image_rgb._original) == len(image_rgb._images) == len(image_rgb._colors) == n_images
        for color in colors:
            assert color in image_rgb._colors

    @staticmethod
    def test_init_images_colors_fail():
        with pytest.raises(ValueError):
            images = get_images(1)
            colors = get_colors(2)
            _ = ImageRGBA(images, colors)

    @staticmethod
    @pytest.mark.parametrize("n_images", (1, 3, 5))
    def test_intensities(n_images):
        images = get_images(n_images)
        image_rgb = ImageRGBA(images)

        assert_array_equal(np.sum(images, axis=0), image_rgb.intensities)

    @staticmethod
    @pytest.mark.parametrize("n_images", (1, 3, 5))
    def test_rgb(n_images):
        images = get_images(n_images)
        image_rgb = ImageRGBA(images)

        rgba = image_rgb.rgba
        assert rgba.shape[2] == 4
        assert rgba.max() <= 255
        assert rgba.min() >= 0
        assert rgba.dtype == np.uint8

        rgb = image_rgb.rgb
        assert rgb.shape[2] == 3
        assert rgb.max() <= 255
        assert rgb.min() >= 0
        assert rgb.dtype == np.uint8

        image_rgb.reset()
        assert image_rgb._rgba is None

    @staticmethod
    @pytest.mark.parametrize("n_images", (1, 3, 5))
    @pytest.mark.parametrize("max_value, dtype", ([255, np.uint8], [65535, np.uint16]))
    def test_combine(n_images, max_value, dtype):
        images = get_images(n_images)
        image_rgb = ImageRGBA(images)
        rgba = image_rgb.combine(max_value, dtype)

        assert rgba.shape == (10, 10, 4)
        assert rgba.min() >= 0
        assert rgba.max() <= max_value
        assert rgba.dtype == dtype

    @staticmethod
    @pytest.mark.parametrize("n_images", (1, 3, 5))
    @pytest.mark.parametrize("channel", (0, 1, 2))
    def test_normalize_channel(n_images, channel):
        images = get_images(n_images)
        image_rgb = ImageRGBA(images)

        image_rgb.clip_channel(channel, 20, 100)
        assert image_rgb.rgba[:, :, channel].min() >= 20
        assert image_rgb.rgba[:, :, channel].max() <= 100

    @staticmethod
    @pytest.mark.parametrize("n_images", (1, 3, 5))
    def test_equalize_histogram(n_images):
        images = get_images(n_images)
        image_rgb = ImageRGBA(images)

        image = image_rgb.equalize_histogram()
        assert image.min() >= 0
        assert image.max() <= 255

    @staticmethod
    @pytest.mark.parametrize("n_images", (1, 3, 5))
    @pytest.mark.parametrize("clip_limit", (0.01, 0.5))
    def test_adaptive_histogram(n_images, clip_limit):
        images = get_images(n_images)
        image_rgb = ImageRGBA(images)

        image = image_rgb.adaptive_histogram(clip_limit=clip_limit)
        assert image.min() >= 0
        assert image.max() <= 255

    @staticmethod
    @pytest.mark.parametrize("n_images", (1, 3, 5))
    def test_quantile_rescale(n_images):
        images = get_images(n_images)
        image_rgb = ImageRGBA(images)

        image = image_rgb.quantile_rescale()
        assert image.min() >= 0
        assert image.max() <= 255

    @staticmethod
    @pytest.mark.parametrize("n_images", (1, 3, 5))
    @pytest.mark.parametrize("q_low", (-0.5, 1.01))
    @pytest.mark.parametrize("q_high", (-0.3, 1.5))
    def test_quantile_rescale_fail(n_images, q_low, q_high):
        images = get_images(n_images)
        image_rgb = ImageRGBA(images)

        with pytest.raises(ValueError):
            image_rgb.quantile_rescale(q_low, q_high)

    @staticmethod
    def test_recolor():
        images = get_images(2)
        colors = ["#FF0000", "#00FF00"]
        image_rgb = ImageRGBA(images, colors)
        assert image_rgb._colors[0] == colors[0]
        assert image_rgb._colors[1] == colors[1]
        new_color = "#FFFF00"
        image_rgb.recolor(0, new_color)
        assert image_rgb._colors[0] == new_color

        new_color = [1, 0, 1]
        image_rgb.recolor(0, new_color)
        assert image_rgb._colors[0] == new_color

        with pytest.raises(ValueError):
            image_rgb.recolor(3, new_color)

        with pytest.raises(ValueError):
            image_rgb.recolor(0, (255, 1, 0))

    @staticmethod
    def test_get_one():
        images = get_images(2)
        image_rgb = ImageRGBA(images)

        im = image_rgb.get_one(0, keep_alpha=True)
        assert im.shape[2] == 4
        im = image_rgb.get_one(0, keep_alpha=False)
        assert im.shape[2] == 3

        with pytest.raises(ValueError):
            image_rgb.get_one(3)

    @staticmethod
    @pytest.mark.parametrize("n_bins", (12, 256))
    def test_get_colormap(n_bins):
        images = get_images(2)
        image_rgb = ImageRGBA(images)

        colormap = image_rgb.get_colormap(0, n_bins)
        assert isinstance(colormap, ListedColormap)
        assert len(colormap.colors) == n_bins

        with pytest.raises(ValueError):
            image_rgb.get_colormap(2, n_bins)
