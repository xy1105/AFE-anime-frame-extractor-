# ui/widgets.py
from PyQt5.QtWidgets import (QSlider, QStyleOptionSlider, QStyle, QLabel,
                             QProgressBar, QApplication)
from PyQt5.QtCore import Qt, QRect, QPropertyAnimation, QEasingCurve, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush

class AEStyleSlider(QSlider):
    """A slider mimicking After Effects style with a value tooltip."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)
        self._pressed = False
        self._hover_pos = QPoint()

        # Tooltip setup (using parent's coordinate system for better placement)
        self._tooltip_label = QLabel(self.parentWidget()) # Attach to parent for overlay
        self._tooltip_label.setStyleSheet("""
            background-color: rgba(0, 0, 0, 180);
            color: white;
            padding: 3px 5px;
            border-radius: 3px;
            font-size: 9pt;
        """)
        self._tooltip_label.setAlignment(Qt.AlignCenter)
        self._tooltip_label.setVisible(False)
        self._tooltip_label.setAttribute(Qt.WA_TransparentForMouseEvents) # Ignore mouse events

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Allow clicking anywhere on the groove to set value
            option = QStyleOptionSlider()
            self.initStyleOption(option)
            groove_rect = self.style().subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderGroove, self)
            handle_rect = self.style().subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderHandle, self)

            # Check if click is on handle or groove
            if handle_rect.contains(event.pos()) or groove_rect.contains(event.pos()):
                 # Calculate value based on click position within the available slider range
                new_value = self._pixelPosToRangeValue(event.pos())
                if new_value != self.value():
                    self.setValue(new_value)
                self._pressed = True
                self._update_tooltip(event.pos())
                event.accept()
                # Need to call super properly for dragging to work if pressed on handle
                # return super().mousePressEvent(event) # Let super handle handle press
            else:
                event.ignore() # Click outside relevant area
                super().mousePressEvent(event) # Let parent handle maybe?
        else:
            super().mousePressEvent(event)


    def mouseMoveEvent(self, event):
        self._hover_pos = event.pos()
        if self._pressed:
             # Calculate value based on drag position
            new_value = self._pixelPosToRangeValue(event.pos())
            if new_value != self.value():
                self.setValue(new_value)
            self._update_tooltip(event.pos())
            event.accept()
        else:
            # Show tooltip on hover even if not pressed
            self._update_tooltip(event.pos())
            super().mouseMoveEvent(event)


    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._pressed:
                self._pressed = False
                self._tooltip_label.setVisible(False)
                event.accept()
                # Recalculate value one last time on release
                # new_value = self._pixelPosToRangeValue(event.pos())
                # if new_value != self.value():
                #     self.setValue(new_value)
                # return super().mouseReleaseEvent(event) # Let super handle cleanup if needed
            else:
                event.ignore()
        super().mouseReleaseEvent(event)


    def enterEvent(self, event):
        # Ensure tooltip is attached to the correct parent if layout changes happened
        if self._tooltip_label.parentWidget() != self.parentWidget():
            self._tooltip_label.setParent(self.parentWidget())
        self._update_tooltip(self.mapFromGlobal(self.cursor().pos())) # Initial position
        self._tooltip_label.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        # Hide tooltip only if not currently being pressed (covers edge case)
        if not self._pressed:
             self._tooltip_label.setVisible(False)
        super().leaveEvent(event)

    def _update_tooltip(self, local_pos):
        """Updates the tooltip's text and position."""
        if not self.isEnabled(): # Don't show if disabled
             self._tooltip_label.setVisible(False)
             return

        # Get current value (either actual or potential based on hover)
        # Use actual value for simplicity now
        current_value_text = str(self.value())
        self._tooltip_label.setText(current_value_text)
        self._tooltip_label.adjustSize() # Fit text

        # Calculate position above the slider handle or hover position
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        handle_rect = self.style().subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderHandle, self)

        # Position tooltip centered above the handle
        handle_center_x = handle_rect.center().x()
        tooltip_x = handle_center_x - self._tooltip_label.width() // 2
        tooltip_y = handle_rect.y() - self._tooltip_label.height() - 5 # 5px spacing above

        # Map local slider coordinates to parent widget coordinates for the tooltip
        global_pos = self.mapToParent(QPoint(tooltip_x, tooltip_y))

        # Keep tooltip within parent bounds (simple check)
        parent_width = self.parentWidget().width() if self.parentWidget() else self.width() # Fallback
        global_pos.setX(max(0, min(global_pos.x(), parent_width - self._tooltip_label.width())))

        self._tooltip_label.move(global_pos)
        self._tooltip_label.setVisible(True)
        self._tooltip_label.raise_() # Ensure it's on top


    def _pixelPosToRangeValue(self, pos):
        """Converts a pixel position along the slider axis to its corresponding value."""
        option = QStyleOptionSlider()
        self.initStyleOption(option)

        # Get the groove geometry
        groove_rect = self.style().subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderGroove, self)
        # Get the handle geometry (useful for finding the center of the movable range)
        handle_rect = self.style().subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderHandle, self)

        if self.orientation() == Qt.Horizontal:
            # Calculate the available slider span in pixels
            slider_min_pos = groove_rect.x()
            slider_max_pos = groove_rect.right() - handle_rect.width() # End position of the handle's left edge
            slider_length_pixels = slider_max_pos - slider_min_pos
            # Adjust click position relative to the start of the span
            pixel_offset = pos.x() - slider_min_pos - handle_rect.width() // 2 # Center click relative to handle

        else: # Vertical orientation (not used here but for completeness)
            slider_min_pos = groove_rect.y()
            slider_max_pos = groove_rect.bottom() - handle_rect.height()
            slider_length_pixels = slider_max_pos - slider_min_pos
            pixel_offset = pos.y() - slider_min_pos - handle_rect.height() // 2

        if slider_length_pixels <= 0:
            return self.minimum() # Avoid division by zero

        # Calculate the position ratio (0.0 to 1.0)
        pos_ratio = max(0.0, min(1.0, pixel_offset / slider_length_pixels))

        # Map the ratio to the slider's value range
        value_range = self.maximum() - self.minimum()
        value = self.minimum() + pos_ratio * value_range

        # Handle slider inversion if necessary (usually not for horizontal)
        if option.upsideDown:
            value = self.maximum() - (value - self.minimum())

        # Ensure value is within bounds and snap to tick intervals if enabled
        # We will round to nearest integer for simplicity here
        final_value = round(max(self.minimum(), min(self.maximum(), value)))

        # Snap to single step if enabled
        if self.singleStep() > 0:
             steps = round((final_value - self.minimum()) / self.singleStep())
             final_value = self.minimum() + steps * self.singleStep()


        # Clamp again after step snapping
        return int(max(self.minimum(), min(self.maximum(), final_value)))

class AnimatedProgressBar(QProgressBar):
    """A QProgressBar with smooth value transitions."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setEasingCurve(QEasingCurve.InOutQuad)
        self._animation.setDuration(300)  # 300ms animation duration

    def setValue(self, value):
        """Sets the progress bar value with animation."""
        # Stop existing animation before starting a new one
        if self._animation.state() == QPropertyAnimation.Running:
            self._animation.stop()

        # Only animate if the value changes significantly (optional optimization)
        #if abs(value - self.value()) > 1:
        self._animation.setStartValue(self.value())
        self._animation.setEndValue(int(value)) # Ensure integer value
        self._animation.start()
        #else:
            # If change is small, set directly to avoid jerky animation start/stop
            # super().setValue(int(value))


    # Override the default setValue to prevent direct setting without animation
    # This might be needed if external code calls setValue directly
    def value(self):
        # Return the target value if animating, otherwise current value
        if self._animation.state() == QPropertyAnimation.Running:
            return self._animation.endValue()
        return super().value()