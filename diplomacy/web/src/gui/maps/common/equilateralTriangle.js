export class EquilateralTriangle {
    /** Helper class that represent an equilateral triangle.;
     Used to compute intersection of a line with a side of convoy symbol, which is an equilateral triangle. **/
    constructor(x_top, y_top, x_right, y_right, x_left, y_left) {
        this.x_A = x_top;
        this.y_A = y_top;
        this.x_B = x_right;
        this.y_B = y_right;
        this.x_C = x_left;
        this.y_C = y_left;
        this.h = this.y_B - this.y_A;
        this.x_O = this.x_A;
        this.y_O = this.y_A + 2 * this.h / 3;
        this.line_AB_a = (this.y_B - this.y_A) / (this.x_B - this.x_A);
        this.line_AB_b = this.y_B - this.x_B * this.line_AB_a;
        this.line_AC_a = (this.y_C - this.y_A) / (this.x_C - this.x_A);
        this.line_AC_b = this.y_C - this.x_C * this.line_AC_a;
    }

    __line_OM(x_M, y_M) {
        const a = (y_M - this.y_O) / (x_M - this.x_O);
        const b = y_M - a * x_M;
        return [a, b];
    }

    __intersection_with_AB(x_M, y_M) {
        const [a, b] = [this.line_AB_a, this.line_AB_b];
        let x = null;
        if (x_M === this.x_O) {
            x = x_M;
        } else {
            const [u, v] = this.__line_OM(x_M, y_M);
            if (a === u)
                return [null, null];
            x = (v - b) / (a - u);
        }
        const y = a * x + b;
        if (this.x_A <= x && x <= this.x_B && this.y_A <= y && y <= this.y_B)
            return [x, y];
        return [null, null];
    }

    __intersection_with_AC(x_M, y_M) {
        const [a, b] = [this.line_AC_a, this.line_AC_b];
        let x = null;
        if (x_M === this.x_O) {
            x = x_M;
        } else {
            const [u, v] = this.__line_OM(x_M, y_M);
            if (a === u)
                return [null, null];
            x = (v - b) / (a - u);
        }
        const y = a * x + b;
        if (this.x_C <= x && x <= this.x_A && this.y_A <= y && y <= this.y_C)
            return [x, y];
        return [null, null];
    }

    __intersection_with_BC(x_M, y_M) {
        const y = this.y_C;
        let x = null;
        if (x_M === this.x_O) {
            x = x_M;
        } else {
            const [a, b] = this.__line_OM(x_M, y_M);
            if (a === 0)
                return [null, null];
            x = (y - b) / a;
        }
        if (this.x_C <= x && x <= this.x_A)
            return [x, y];
        return [null, null];
    }

    intersection(x_M, y_M) {
        if (this.x_O === x_M && this.y_O === y_M)
            return [x_M, y_M];
        if (this.x_O === x_M) {
            if (y_M < this.y_O)
                return [x_M, this.y_A];
            else {
                // vertical line intersects BC;
                return [x_M, this.y_C];
            }
        } else if (this.y_O === y_M) {
            let a = null;
            let b = null;
            if (x_M < this.x_O) {
                // horizontal line intersects AC;
                [a, b] = [this.line_AC_a, this.line_AC_b];
            } else {
                // horizontal line intersects AB;
                [a, b] = [this.line_AB_a, this.line_AB_b];
            }
            const x = (y_M - b) / a;
            return [x, y_M];
        } else {
            // get nearest point in intersections with AB, AC, BC;
            const [p1_x, p1_y] = this.__intersection_with_AB(x_M, y_M);
            const [p2_x, p2_y] = this.__intersection_with_AC(x_M, y_M);
            const [p3_x, p3_y] = this.__intersection_with_BC(x_M, y_M);
            const distances = [];
            if (p1_x !== null) {
                const d1 = Math.sqrt((p1_x - x_M) * (p1_x - x_M) + (p1_y - y_M) * (p1_y - y_M));
                distances.push([d1, p1_x, p1_y]);
            }
            if (p2_x !== null) {
                const d2 = Math.sqrt((p2_x - x_M) * (p2_x - x_M) + (p2_y - y_M) * (p2_y - y_M));
                distances.push([d2, p2_x, p2_y]);
            }
            if (p3_x !== null) {
                const d3 = Math.sqrt((p3_x - x_M) * (p3_x - x_M) + (p3_y - y_M) * (p3_y - y_M));
                distances.push([d3, p3_x, p3_y]);
            }
            distances.sort();
            const output = distances[0];
            output.shift();
            return output;
        }
    }
}
