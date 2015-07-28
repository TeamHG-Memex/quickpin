import 'dart:async';
import 'dart:html';

import 'package:angular/angular.dart';

/// A component that converts Markdown text into HTML.
@Component(
    selector: 'masonry',
    template: '<content></content>',
    useShadowDom: false
)
class MasonryComponent implements ShadowRootAware {
    @NgOneWay('column-width')
    int columnWidth;

    @NgOneWay('column-gap')
    int columnGap;

    @NgOneWay('margin-bottom')
    int marginBottom;

    num _columnCount;
    num _columnWidth;
    Element _element;
    List<int> _lastLayout;
    num _parentWidth = -1;
    num _tileCount;

    MasonryComponent(this._element);

    /// Get references to child elements.
    void onShadowRoot(HtmlElement shadowRoot) {
        new Future(() {
            if (this.marginBottom == null) {
                this.marginBottom = this.columnGap;
            }

            this.setChildrenWidths();
        });

        window.onResize.listen(this.setChildrenWidths);
    }

    /// Arrange children into columns.
    void positionChildren() {
        List<int> columnHeights = new List<int>.filled(this._columnCount, 0);

        /// Position elements.
        for (HtmlElement child in this._element.children) {
            if (child is ScriptElement) {
                continue;
            }

            // Find the shortest column
            int shortestColumn = 0;

            for (int i=1; i<this._columnCount; i++) {
                if (columnHeights[i] < columnHeights[shortestColumn]) {
                    shortestColumn = i;
                }
            }

            // Resize this child and put it in this column.
            num left = shortestColumn * (this._columnWidth + this.columnGap);
            num top = columnHeights[shortestColumn];

            child.style.position = 'absolute';
            child.style.left = '${left}px';
            child.style.top = '${top}px';

            columnHeights[shortestColumn] += child.getBoundingClientRect().height + this.marginBottom;
        }

        /// Check if the layout has settled. (Things like element height can
        /// change slowly after changing the element width. We may need to
        /// render a few times until all elements finish resizing.)
        if (this._lastLayout == null ||
            !this._listsAreEqual(this._lastLayout, columnHeights)) {

            this._lastLayout = columnHeights;
            new Timer(new Duration(milliseconds:100), this.positionChildren);
        }
    }

    /// Compute and set desired width of child elements.
    void setChildrenWidths([Event e]) {
        num parentWidth = this._element.getBoundingClientRect().width;

        if ((parentWidth - this._parentWidth).abs() < 0.1) {
            // No need to redo layout.
            return;
        }

        if (parentWidth == 0) {
            // Still waiting for DOM to settle. Try again later.
            new Timer(new Duration(milliseconds: 100), this.setChildrenWidths);
            return;
        }

        num unitWidth = this.columnWidth + this.columnGap;
        this._columnCount = (parentWidth / unitWidth).round();
        num columnPixels = parentWidth - (this.columnGap * (this._columnCount - 1));
        this._columnWidth = columnPixels / this._columnCount;
        this._tileCount = 0;


        for (HtmlElement child in this._element.children) {
            if (child is ScriptElement) {
                continue;
            }

            this._tileCount++;
            child.style.width = '${this._columnWidth}px';
        }

        if (this._tileCount == 0) {
            // Still waiting for DOM to settle. Try again later.
            new Timer(new Duration(milliseconds: 100), this.setChildrenWidths);
            return;
        }

        this._parentWidth = parentWidth;
        new Timer(new Duration(milliseconds: 100), this.positionChildren);
    }

    bool _listsAreEqual(List l1, List l2) {
        if (l1.length != l2.length) {
            return false;
        } else {
            for (int i=0; i<l1.length; i++) {
                if (l1[i] != l2[i]) {
                    return false;
                }
            }
        }

        return true;
    }
}
