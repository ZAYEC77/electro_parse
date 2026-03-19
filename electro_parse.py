from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class GridGeometry:
    cell_width: int
    cell_height: int
    matrix_left: int
    matrix_top: int
    row_count: int
    column_count: int


def quantize_image(image: np.ndarray, max_colors: int = 10) -> np.ndarray:
    pixels = image.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, labels, centers = cv2.kmeans(
        pixels,
        max_colors,
        None,
        criteria,
        5,
        cv2.KMEANS_PP_CENTERS,
    )
    palette = np.uint8(centers)
    return palette[labels.flatten()].reshape(image.shape)


def _extract_filled_components(image: np.ndarray) -> list[tuple[int, int, int, int, int]]:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Filled schedule cells stay noticeably farther from paper white than grid lines.
    mask = (
        ((gray < 235) & (np.abs(image[:, :, 0].astype(int) - image[:, :, 1].astype(int)) > 5))
        | ((hsv[:, :, 1] > 20) & (hsv[:, :, 2] < 250))
    )
    cleaned = cv2.morphologyEx(
        (mask.astype(np.uint8) * 255),
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)),
    )

    component_count, _, stats, _ = cv2.connectedComponentsWithStats(cleaned)
    components: list[tuple[int, int, int, int, int]] = []
    for index in range(1, component_count):
        x, y, width, height, area = stats[index]
        if area > 200 and width >= 30 and height >= 20 and width < 400 and height < 300:
            components.append((int(x), int(y), int(width), int(height), int(area)))
    if not components:
        raise ValueError("Failed to find filled schedule cells in the image.")
    return components


def _infer_step(values: list[int], minimum: int, maximum: int) -> int:
    samples = np.array(values, dtype=float)
    best_step: int | None = None
    best_score: float | None = None

    for step in range(minimum, maximum + 1):
        score = np.abs(samples / step - np.round(samples / step)).mean()
        if best_score is None or score < best_score:
            best_score = score
            best_step = step

    if best_step is None:
        raise ValueError("Failed to infer the grid step.")
    return best_step


def _infer_geometry(
    original_image: np.ndarray,
    quantized_image: np.ndarray,
    row_count: int,
    column_count: int,
) -> GridGeometry:
    try:
        components = _extract_filled_components(quantized_image)
        if len(components) < 2:
            raise ValueError("Not enough filled components for reliable geometry inference.")
        base_width = _infer_step([width for _, _, width, _, _ in components], 20, 60)
        base_height = _infer_step([height for _, _, _, height, _ in components], 20, 60)

        min_x = min(x for x, _, _, _, _ in components)
        max_x = max(x + width for x, _, width, _, _ in components)
        min_y = min(y for _, y, _, _, _ in components)
        max_y = max(y + height for _, y, _, height, _ in components)

        gray = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)
        best_geometry: tuple[float, int, int, int, int] | None = None

        for cell_width in range(max(20, base_width - 2), min(60, base_width + 2) + 1):
            search_from = max(0, max_x - column_count * cell_width - 5)
            search_to = min(min_x, original_image.shape[1] - column_count * cell_width - 1)
            if search_from > search_to:
                continue

            for cell_height in range(max(20, base_height - 1), min(60, base_height + 1) + 1):
                top_candidates = []
                for offset in range(cell_height):
                    for top in range(offset, min_y + 1, cell_height):
                        if top + row_count * cell_height >= max_y:
                            top_candidates.append(top)
                if not top_candidates:
                    continue

                matrix_top = max(top_candidates)
                header_top = max(0, int(round(matrix_top - 3.0 * cell_height)))
                header_bottom = max(header_top + 5, int(round(matrix_top - 0.3 * cell_height)))

                best_left_for_shape: tuple[float, int] | None = None
                for matrix_left in range(search_from, search_to + 1):
                    values = []
                    for column in range(column_count):
                        left = matrix_left + column * cell_width + max(2, cell_width // 10)
                        right = matrix_left + (column + 1) * cell_width - max(2, cell_width // 10)
                        if right <= left:
                            values = []
                            break
                        patch = gray[header_top:header_bottom, left:right]
                        values.append(float((255 - patch).mean()))
                    if not values:
                        continue
                    scores = np.array(values)
                    score = float(scores.mean() - 2.0 * scores.std())
                    if best_left_for_shape is None or score > best_left_for_shape[0]:
                        best_left_for_shape = (score, matrix_left)

                if best_left_for_shape is None:
                    continue

                score, matrix_left = best_left_for_shape
                candidate = (score, cell_width, cell_height, matrix_left, matrix_top)
                if best_geometry is None or score > best_geometry[0]:
                    best_geometry = candidate

        if best_geometry is not None:
            _, cell_width, cell_height, matrix_left, matrix_top = best_geometry
            return GridGeometry(
                cell_width=cell_width,
                cell_height=cell_height,
                matrix_left=matrix_left,
                matrix_top=matrix_top,
                row_count=row_count,
                column_count=column_count,
            )
    except ValueError:
        pass

    return _infer_geometry_from_grid(original_image, row_count=row_count, column_count=column_count)


def _group_centers(indices: np.ndarray) -> list[int]:
    if len(indices) == 0:
        return []

    groups: list[int] = []
    start = int(indices[0])
    previous = int(indices[0])
    for value in indices[1:]:
        current = int(value)
        if current <= previous + 1:
            previous = current
            continue
        groups.append((start + previous) // 2)
        start = current
        previous = current
    groups.append((start + previous) // 2)
    return groups


def _best_uniform_run(gaps: list[int], run_length: int, minimum: int, maximum: int) -> tuple[int, int]:
    best: tuple[float, int, int] | None = None
    for start in range(0, len(gaps) - run_length + 1):
        run = np.array(gaps[start : start + run_length], dtype=float)
        median = int(round(float(np.median(run))))
        if median < minimum or median > maximum:
            continue
        score = float(run.std() + np.abs(run - median).mean())
        candidate = (score, start, median)
        if best is None or score < best[0]:
            best = candidate

    if best is None:
        raise ValueError("Failed to find a uniform grid run.")
    _, start, step = best
    return start, step


def _infer_geometry_from_grid(
    original_image: np.ndarray,
    *,
    row_count: int,
    column_count: int,
) -> GridGeometry:
    gray = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)
    inverted = 255 - gray
    thresholded = cv2.adaptiveThreshold(
        inverted,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        -5,
    )

    height, width = gray.shape
    vertical = cv2.morphologyEx(
        thresholded,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(10, height // 25))),
    )
    horizontal = cv2.morphologyEx(
        thresholded,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(10, width // 25), 1)),
    )
    grid = cv2.add(vertical, horizontal)

    contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("Failed to infer the schedule matrix geometry.")

    contour = max(contours, key=cv2.contourArea)
    box_x, box_y, box_width, box_height = cv2.boundingRect(contour)
    if box_width * box_height < original_image.shape[0] * original_image.shape[1] * 0.05:
        raise ValueError("Failed to infer the schedule matrix geometry.")

    roi = grid[box_y : box_y + box_height, box_x : box_x + box_width]
    x_indices = np.where((roi > 0).sum(axis=0) > box_height * 0.35)[0]
    y_indices = np.where((roi > 0).sum(axis=1) > box_width * 0.35)[0]
    x_lines = _group_centers(x_indices)
    y_lines = _group_centers(y_indices)

    x_gaps = [x_lines[index + 1] - x_lines[index] for index in range(len(x_lines) - 1)]
    y_gaps = [y_lines[index + 1] - y_lines[index] for index in range(len(y_lines) - 1)]
    x_start, cell_width = _best_uniform_run(x_gaps, column_count, minimum=20, maximum=90)
    y_start, cell_height = _best_uniform_run(y_gaps, row_count, minimum=20, maximum=90)

    return GridGeometry(
        cell_width=cell_width,
        cell_height=cell_height,
        matrix_left=box_x + x_lines[x_start],
        matrix_top=box_y + y_lines[y_start],
        row_count=row_count,
        column_count=column_count,
    )


def _sample_cell_colors(image: np.ndarray, geometry: GridGeometry) -> list[list[np.ndarray]]:
    cell_colors: list[list[np.ndarray]] = []
    x_padding = max(2, geometry.cell_width // 4)
    y_padding = max(2, geometry.cell_height // 4)
    image_height, image_width = image.shape[:2]

    for row in range(geometry.row_count):
        row_colors: list[np.ndarray] = []
        for column in range(geometry.column_count):
            left = max(0, geometry.matrix_left + column * geometry.cell_width + x_padding)
            right = min(image_width, geometry.matrix_left + (column + 1) * geometry.cell_width - x_padding)
            top = max(0, geometry.matrix_top + row * geometry.cell_height + y_padding)
            bottom = min(image_height, geometry.matrix_top + (row + 1) * geometry.cell_height - y_padding)
            patch = image[top:bottom, left:right]
            if patch.size == 0:
                row_colors.append(np.array([255.0, 255.0, 255.0]))
            else:
                row_colors.append(np.median(patch.reshape(-1, 3), axis=0))
        cell_colors.append(row_colors)
    return cell_colors


def _draw_debug_overlay(
    image: np.ndarray,
    geometry: GridGeometry,
    cell_colors: list[list[np.ndarray]],
    off_colors: set[tuple[int, int, int]],
    maybe_colors: set[tuple[int, int, int]],
    output_path: Path,
) -> None:
    debug_image = image.copy()
    left = geometry.matrix_left
    top = geometry.matrix_top
    right = left + geometry.column_count * geometry.cell_width
    bottom = top + geometry.row_count * geometry.cell_height

    point_colors = {
        "off": (0, 0, 255),
        "maybe_off": (255, 0, 0),
        "on": (0, 180, 0),
    }
    cv2.rectangle(debug_image, (left, top), (right, bottom), (0, 0, 255), 2)

    for column in range(geometry.column_count + 1):
        x = left + column * geometry.cell_width
        cv2.line(debug_image, (x, top), (x, bottom), (0, 180, 255), 1)

    for row in range(geometry.row_count + 1):
        y = top + row * geometry.cell_height
        cv2.line(debug_image, (left, y), (right, y), (0, 180, 255), 1)

    x_padding = max(2, geometry.cell_width // 4)
    y_padding = max(2, geometry.cell_height // 4)
    for row in range(geometry.row_count):
        for column in range(geometry.column_count):
            sample_left = left + column * geometry.cell_width + x_padding
            sample_right = left + (column + 1) * geometry.cell_width - x_padding
            sample_top = top + row * geometry.cell_height + y_padding
            sample_bottom = top + (row + 1) * geometry.cell_height - y_padding
            cx = (sample_left + sample_right) // 2
            cy = (sample_top + sample_bottom) // 2
            color = tuple(int(channel) for channel in np.uint8(cell_colors[row][column]).tolist())
            if color in off_colors:
                status = "off"
            elif color in maybe_colors:
                status = "maybe_off"
            else:
                status = "on"
            cv2.circle(debug_image, (cx, cy), 3, point_colors[status], -1)

    if not cv2.imwrite(str(output_path), debug_image):
        raise ValueError(f"Failed to write debug image: {output_path}")


def _classify_palette(cell_colors: list[list[np.ndarray]]) -> tuple[set[tuple[int, int, int]], set[tuple[int, int, int]]]:
    flat = [tuple(np.uint8(color).tolist()) for row in cell_colors for color in row]
    unique_colors, counts = np.unique(np.array(flat, dtype=np.uint8), axis=0, return_counts=True)

    if len(unique_colors) == 0:
        return set(), set()

    distances_to_white = np.linalg.norm(unique_colors.astype(np.float32) - 255.0, axis=1)
    hsv_colors = cv2.cvtColor(unique_colors.reshape(-1, 1, 3), cv2.COLOR_BGR2HSV).reshape(-1, 3)

    background_index = int(np.argmin(distances_to_white))
    non_background = [
        index for index in range(len(unique_colors)) if index != background_index and distances_to_white[index] > 20.0
    ]

    if not non_background:
        return set(), set()

    ordered = sorted(
        non_background,
        key=lambda index: (int(hsv_colors[index][1]), float(distances_to_white[index]), int(counts[index])),
        reverse=True,
    )

    off_colors = {tuple(int(channel) for channel in unique_colors[ordered[0]])}
    maybe_colors = {tuple(int(channel) for channel in unique_colors[index]) for index in ordered[1:]}
    return off_colors, maybe_colors


def _row_labels(row_count: int) -> list[str]:
    return [f"{row // 2 + 1}.{row % 2 + 1}" for row in range(row_count)]


def parse_schedule_image(
    image_path: str | Path,
    *,
    row_count: int = 12,
    column_count: int = 24,
    max_colors: int = 10,
    debug_output: str | Path | None = None,
) -> dict[str, dict[str, list[str]]]:
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"Failed to read image: {image_path}")

    quantized = quantize_image(image, max_colors=max_colors)
    geometry = _infer_geometry(image, quantized, row_count=row_count, column_count=column_count)
    cell_colors = _sample_cell_colors(quantized, geometry)
    off_colors, maybe_colors = _classify_palette(cell_colors)
    if debug_output is not None:
        _draw_debug_overlay(image, geometry, cell_colors, off_colors, maybe_colors, Path(debug_output))

    result: dict[str, dict[str, list[str]]] = {}
    for row_index, label in enumerate(_row_labels(row_count)):
        off_hours: list[str] = []
        maybe_off_hours: list[str] = []
        for hour in range(column_count):
            color = tuple(int(channel) for channel in np.uint8(cell_colors[row_index][hour]).tolist())
            hour_label = f"{hour:02d}:00"
            if color in off_colors:
                off_hours.append(hour_label)
            elif color in maybe_colors:
                maybe_off_hours.append(hour_label)
        result[label] = {"off": off_hours, "maybe_off": maybe_off_hours}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse a daily power outage schedule image.")
    parser.add_argument("image", type=Path, help="Path to the JPEG/PNG schedule image")
    parser.add_argument("--rows", type=int, default=12, help="Number of matrix rows to parse")
    parser.add_argument("--columns", type=int, default=24, help="Number of hour columns to parse")
    parser.add_argument("--max-colors", type=int, default=10, help="Palette size for image quantization")
    parser.add_argument(
        "--debug",
        nargs="?",
        const="auto",
        default=None,
        help="Write a copy of the image with detected grid overlay. Optional value sets output path.",
    )
    args = parser.parse_args()

    debug_output: Path | None = None
    if args.debug is not None:
        debug_output = (
            args.image.with_name(f"{args.image.stem}.debug{args.image.suffix}")
            if args.debug == "auto"
            else Path(args.debug)
        )

    parsed = parse_schedule_image(
        args.image,
        row_count=args.rows,
        column_count=args.columns,
        max_colors=args.max_colors,
        debug_output=debug_output,
    )
    print(json.dumps(parsed, ensure_ascii=False, indent=2))
    if debug_output is not None:
        print(f"debug_image={debug_output}", flush=True)


if __name__ == "__main__":
    main()
