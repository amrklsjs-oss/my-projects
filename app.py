from __future__ import annotations

from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


st.set_page_config(
    page_title="Image Processing Studio",
    page_icon="IP",
    layout="wide",
)


CSS = """
<style>
    .stApp {
        background: #0f1020;
        color: #f7f2ff;
    }
    [data-testid="stHeader"] {
        background: rgba(15, 16, 32, 0.88);
    }
    section[data-testid="stSidebar"] {
        background: #15142a;
        border-right: 1px solid rgba(196, 142, 255, 0.2);
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .title-band {
        background: linear-gradient(135deg, #300047 0%, #8426c4 100%);
        border: 1px solid rgba(232, 204, 255, 0.22);
        border-radius: 8px;
        padding: 1.35rem 1.5rem;
        margin-bottom: 1.25rem;
    }
    .title-band h1 {
        margin: 0;
        font-size: 2rem;
        letter-spacing: 0;
    }
    .title-band p {
        margin: 0.35rem 0 0 0;
        color: #efe1ff;
    }
    .metric-strip {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.75rem;
        margin: 0.5rem 0 1rem;
    }
    .metric-card {
        border: 1px solid rgba(196, 142, 255, 0.32);
        border-radius: 8px;
        padding: 0.8rem 0.9rem;
        background: rgba(255, 255, 255, 0.035);
    }
    .metric-card span {
        display: block;
        color: #d9c2ff;
        font-size: 0.78rem;
    }
    .metric-card strong {
        display: block;
        margin-top: 0.25rem;
        color: #ffffff;
        font-size: 1rem;
        word-break: break-word;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.35rem;
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px 8px 0 0;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    @media (max-width: 850px) {
        .metric-strip {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }
</style>
"""


def pil_to_png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def make_sample_image(size: int = 640) -> Image.Image:
    y, x = np.mgrid[0:size, 0:size]
    gradient = (x / size * 255).astype(np.uint8)
    rings = ((np.sin(np.sqrt((x - size * 0.5) ** 2 + (y - size * 0.5) ** 2) / 14) + 1) * 80).astype(np.uint8)
    checker = (((x // 64 + y // 64) % 2) * 70).astype(np.uint8)
    red = np.clip(gradient + checker, 0, 255)
    green = np.clip(255 - gradient + rings, 0, 255)
    blue = np.clip((y / size * 255) + checker // 2, 0, 255)
    return Image.fromarray(np.dstack([red, green, blue]).astype(np.uint8), "RGB")


def convolve_gray(gray: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    pad_y, pad_x = kernel.shape[0] // 2, kernel.shape[1] // 2
    padded = np.pad(gray.astype(float), ((pad_y, pad_y), (pad_x, pad_x)), mode="edge")
    output = np.zeros_like(gray, dtype=float)
    for row in range(gray.shape[0]):
        for col in range(gray.shape[1]):
            region = padded[row : row + kernel.shape[0], col : col + kernel.shape[1]]
            output[row, col] = np.sum(region * kernel)
    return np.clip(output, 0, 255).astype(np.uint8)


def sobel_edges(image: Image.Image) -> Image.Image:
    gray = np.asarray(ImageOps.grayscale(image), dtype=float)
    gx_kernel = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
    gy_kernel = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]])
    gx = convolve_gray(gray, gx_kernel).astype(float)
    gy = convolve_gray(gray, gy_kernel).astype(float)
    magnitude = np.sqrt(gx**2 + gy**2)
    magnitude = (magnitude / max(magnitude.max(), 1) * 255).astype(np.uint8)
    return Image.fromarray(magnitude, "L").convert("RGB")


def histogram_equalization(image: Image.Image) -> Image.Image:
    ycbcr = image.convert("YCbCr")
    y, cb, cr = ycbcr.split()
    y_array = np.asarray(y)
    histogram, bins = np.histogram(y_array.flatten(), bins=256, range=[0, 256])
    cdf = histogram.cumsum()
    cdf_masked = np.ma.masked_equal(cdf, 0)
    cdf_masked = (cdf_masked - cdf_masked.min()) * 255 / (cdf_masked.max() - cdf_masked.min())
    lookup = np.ma.filled(cdf_masked, 0).astype(np.uint8)
    equalized_y = Image.fromarray(lookup[y_array], "L")
    return Image.merge("YCbCr", (equalized_y, cb, cr)).convert("RGB")


def gamma_correct(image: Image.Image, gamma: float) -> Image.Image:
    arr = np.asarray(image).astype(float) / 255.0
    corrected = np.power(arr, gamma)
    return Image.fromarray(np.clip(corrected * 255, 0, 255).astype(np.uint8), "RGB")


def kmeans_quantize(image: Image.Image, colors: int, iterations: int = 8) -> Image.Image:
    small = image.copy()
    small.thumbnail((360, 360))
    pixels = np.asarray(small).reshape(-1, 3).astype(float)
    if len(pixels) == 0:
        return image

    seed_indices = np.linspace(0, len(pixels) - 1, colors).astype(int)
    centroids = pixels[seed_indices]
    for _ in range(iterations):
        distances = np.linalg.norm(pixels[:, None, :] - centroids[None, :, :], axis=2)
        labels = distances.argmin(axis=1)
        for idx in range(colors):
            cluster = pixels[labels == idx]
            if len(cluster):
                centroids[idx] = cluster.mean(axis=0)

    full_pixels = np.asarray(image).reshape(-1, 3).astype(float)
    distances = np.linalg.norm(full_pixels[:, None, :] - centroids[None, :, :], axis=2)
    labels = distances.argmin(axis=1)
    quantized = centroids[labels].reshape(np.asarray(image).shape)
    return Image.fromarray(np.clip(quantized, 0, 255).astype(np.uint8), "RGB")


def morphology(image: Image.Image, mode: str, threshold: int, size: int) -> Image.Image:
    binary = ImageOps.grayscale(image).point(lambda pixel: 255 if pixel >= threshold else 0)
    if mode == "Dilation":
        result = binary.filter(ImageFilter.MaxFilter(size))
    elif mode == "Erosion":
        result = binary.filter(ImageFilter.MinFilter(size))
    elif mode == "Opening":
        result = binary.filter(ImageFilter.MinFilter(size)).filter(ImageFilter.MaxFilter(size))
    else:
        result = binary.filter(ImageFilter.MaxFilter(size)).filter(ImageFilter.MinFilter(size))
    return result.convert("RGB")


def sepia(image: Image.Image) -> Image.Image:
    arr = np.asarray(image).astype(float)
    transform = np.array(
        [
            [0.393, 0.769, 0.189],
            [0.349, 0.686, 0.168],
            [0.272, 0.534, 0.131],
        ]
    )
    return Image.fromarray(np.clip(arr @ transform.T, 0, 255).astype(np.uint8), "RGB")


def apply_processing(image: Image.Image, operation: str, settings: dict) -> Image.Image:
    image = image.convert("RGB")

    if operation == "Original":
        return image
    if operation == "Grayscale":
        return ImageOps.grayscale(image).convert("RGB")
    if operation == "Negative":
        return ImageOps.invert(image)
    if operation == "Threshold":
        threshold = settings["threshold"]
        return ImageOps.grayscale(image).point(lambda pixel: 255 if pixel >= threshold else 0).convert("RGB")
    if operation == "Brightness / Contrast":
        bright = ImageEnhance.Brightness(image).enhance(settings["brightness"])
        return ImageEnhance.Contrast(bright).enhance(settings["contrast"])
    if operation == "Gamma Correction":
        return gamma_correct(image, settings["gamma"])
    if operation == "Blur":
        return image.filter(ImageFilter.GaussianBlur(settings["radius"]))
    if operation == "Sharpen":
        return ImageEnhance.Sharpness(image).enhance(settings["sharpness"])
    if operation == "Sobel Edge Detection":
        return sobel_edges(image)
    if operation == "Emboss":
        return image.filter(ImageFilter.EMBOSS)
    if operation == "Histogram Equalization":
        return histogram_equalization(image)
    if operation == "Sepia":
        return sepia(image)
    if operation == "K-Means Color Quantization":
        return kmeans_quantize(image, settings["colors"])
    if operation == "Morphology":
        return morphology(image, settings["morph_mode"], settings["morph_threshold"], settings["morph_size"])
    if operation == "Channel Viewer":
        channel = settings["channel"]
        arr = np.asarray(image)
        channel_index = {"Red": 0, "Green": 1, "Blue": 2}[channel]
        output = np.zeros_like(arr)
        output[:, :, channel_index] = arr[:, :, channel_index]
        return Image.fromarray(output, "RGB")

    return image


def image_stats(image: Image.Image) -> dict[str, str]:
    arr = np.asarray(image.convert("RGB"))
    return {
        "Size": f"{image.width} x {image.height}",
        "Mean RGB": ", ".join(f"{value:.1f}" for value in arr.mean(axis=(0, 1))),
        "Min / Max": f"{arr.min()} / {arr.max()}",
        "Std Dev": f"{arr.std():.1f}",
    }


def plot_histogram(original: Image.Image, processed: Image.Image) -> plt.Figure:
    figure, axes = plt.subplots(1, 2, figsize=(10, 3.2), constrained_layout=True)
    for axis, image, title in zip(axes, [original, processed], ["Original", "Processed"]):
        arr = np.asarray(image.convert("RGB"))
        for color, label, idx in [("#ff5d73", "Red", 0), ("#61d394", "Green", 1), ("#5aa9ff", "Blue", 2)]:
            axis.hist(arr[:, :, idx].ravel(), bins=64, range=(0, 255), alpha=0.62, color=color, label=label)
        axis.set_title(title)
        axis.set_xlabel("Intensity")
        axis.set_ylabel("Pixels")
        axis.grid(alpha=0.18)
    axes[0].legend(loc="upper right", fontsize=8)
    figure.patch.set_facecolor("#0f1020")
    for axis in axes:
        axis.set_facecolor("#17172f")
        axis.tick_params(colors="#f7f2ff")
        axis.xaxis.label.set_color("#f7f2ff")
        axis.yaxis.label.set_color("#f7f2ff")
        axis.title.set_color("#ffffff")
    return figure


def render_metrics(stats: dict[str, str]) -> None:
    st.markdown(
        '<div class="metric-strip">'
        + "".join(
            f'<div class="metric-card"><span>{label}</span><strong>{value}</strong></div>'
            for label, value in stats.items()
        )
        + "</div>",
        unsafe_allow_html=True,
    )


st.markdown(CSS, unsafe_allow_html=True)
st.markdown(
    """
    <div class="title-band">
        <h1>Image Processing Studio</h1>
        <p>Interactive lab project for filtering, enhancement, segmentation, edges, histograms, morphology, and bonus algorithms.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Controls")
    uploaded_file = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg", "bmp", "webp"])
    use_sample = st.toggle("Use generated sample image", value=uploaded_file is None)

    operations = [
        "Original",
        "Grayscale",
        "Negative",
        "Threshold",
        "Brightness / Contrast",
        "Gamma Correction",
        "Blur",
        "Sharpen",
        "Sobel Edge Detection",
        "Emboss",
        "Histogram Equalization",
        "Sepia",
        "K-Means Color Quantization",
        "Morphology",
        "Channel Viewer",
    ]
    operation = st.selectbox("Processing operation", operations)

    settings: dict[str, float | int | str] = {}
    if operation == "Threshold":
        settings["threshold"] = st.slider("Threshold", 0, 255, 128)
    elif operation == "Brightness / Contrast":
        settings["brightness"] = st.slider("Brightness", 0.1, 3.0, 1.15, 0.05)
        settings["contrast"] = st.slider("Contrast", 0.1, 3.0, 1.25, 0.05)
    elif operation == "Gamma Correction":
        settings["gamma"] = st.slider("Gamma", 0.2, 3.0, 0.8, 0.05)
    elif operation == "Blur":
        settings["radius"] = st.slider("Blur radius", 0.0, 12.0, 2.0, 0.25)
    elif operation == "Sharpen":
        settings["sharpness"] = st.slider("Sharpness", 0.0, 6.0, 2.4, 0.1)
    elif operation == "K-Means Color Quantization":
        settings["colors"] = st.slider("Number of colors", 2, 16, 6)
    elif operation == "Morphology":
        settings["morph_mode"] = st.selectbox("Morphology mode", ["Dilation", "Erosion", "Opening", "Closing"])
        settings["morph_threshold"] = st.slider("Binary threshold", 0, 255, 128)
        settings["morph_size"] = st.select_slider("Kernel size", options=[3, 5, 7, 9], value=3)
    elif operation == "Channel Viewer":
        settings["channel"] = st.radio("Channel", ["Red", "Green", "Blue"], horizontal=True)

    st.divider()
    st.caption("Bonus algorithms included: histogram equalization, K-means quantization, morphology, and Sobel edge detection.")


if uploaded_file is not None and not use_sample:
    source_image = Image.open(uploaded_file).convert("RGB")
    filename = uploaded_file.name
else:
    source_image = make_sample_image()
    filename = "generated_sample.png"

processed_image = apply_processing(source_image, operation, settings)

render_metrics(image_stats(processed_image))

preview_tab, histogram_tab, explanation_tab = st.tabs(["Preview", "Histogram", "Algorithm Notes"])

with preview_tab:
    left, right = st.columns(2)
    with left:
        st.subheader("Original")
        st.image(source_image, width="stretch")
    with right:
        st.subheader("Processed")
        st.image(processed_image, width="stretch")

    st.download_button(
        "Download processed PNG",
        data=pil_to_png_bytes(processed_image),
        file_name=f"processed_{filename.rsplit('.', 1)[0]}.png",
        mime="image/png",
        width="stretch",
    )

with histogram_tab:
    st.pyplot(plot_histogram(source_image, processed_image), width="stretch")

with explanation_tab:
    notes = {
        "Original": "Displays the uploaded image without modification for comparison and baseline inspection.",
        "Grayscale": "Converts RGB pixels to one luminance channel, a common first step for segmentation and edge detection.",
        "Negative": "Inverts intensity values so bright areas become dark and dark areas become bright.",
        "Threshold": "Segments an image by converting pixels above a chosen intensity to white and the rest to black.",
        "Brightness / Contrast": "Adjusts global lightness and expands or compresses tonal differences.",
        "Gamma Correction": "Applies a non-linear intensity curve, useful for correcting images that are too dark or washed out.",
        "Blur": "Uses Gaussian smoothing to reduce noise and soften detail.",
        "Sharpen": "Enhances local contrast so edges and fine details become more visible.",
        "Sobel Edge Detection": "Computes horizontal and vertical gradients, then combines them to highlight strong edges.",
        "Emboss": "Applies a directional filter that creates a raised relief effect.",
        "Histogram Equalization": "Redistributes luminance values to improve contrast, especially in low-contrast images.",
        "Sepia": "Transforms RGB channels with a warm color matrix for a classic photographic tone.",
        "K-Means Color Quantization": "Clusters similar colors and replaces each pixel with its closest cluster center.",
        "Morphology": "Performs dilation, erosion, opening, or closing on a thresholded binary image.",
        "Channel Viewer": "Isolates one RGB channel to show how color information is distributed.",
    }
    st.subheader(operation)
    st.write(notes[operation])
    st.write("Current settings")
    st.json(settings or {"mode": "default"})
