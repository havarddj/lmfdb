import svg
import random

from dataclasses import dataclass
# from utils/color import StandardColors

# handy new python feature mimicing c data structures
@dataclass
class Point:
    x: float
    y: float
    girth: float = 1
    color: str = "black"
    def __str__(self):
        return f"Point ({self.x}, {self.y}) of girth {self.girth} and color {self.color}"

def draw_spec(frobs, local_algs, colors=True) -> svg.SVG:
    """ Draw the spectrum of the ring of integers of a number field,
    from data in the lmfdb.
    `frobs` is a list of lists [[p, [frob_cycle1,...,frob_cycleN]]]
    `local_algs` is a list of strings describing ramification behaviour ['p.deg.(other stuff)', ..., ]
    If `colors` is `True`, color classes which lie in the same Frobenius cycle
    """
    num_primes = len(frobs)
    num_colors = max(len(l) for _, l in frobs)
    if colors:
        col_max = max(i[0] for [p,l] in frobs for i in l if l != [0])
    else:
        col_max = 0
    
    ### Options:
    # I've hardcoded these values instead of providing them
    # as optional arguments; feel free to change this
    
    # distance between two primes along x-axis
    x_spread = 50
    
    # distance between prime ideals in same fibre
    # = total distance from top to bottom
    y_spread = 30

    # (absolute) height of svg
    height = 200

    # (absolute) width of svg
    width = (num_primes+3)*x_spread

    # y-coordinate of Spec Z
    bottom_line = round((7/8)*height)

    # fraction of height of centre line around which the primes in spec are centred
    centre_ratio = 3.5/8
    y_centre = round(centre_ratio*height)
    
    # y-coordinate of Spec O_K
    line_thickness = 1

    # increase or decrease girth of ramified primes
    ramify_factor = 1

    # radius of (unramified) points
    dot_radius = 2.5

    # parameter to control the cubic bezier curves.
    # Should probably be between 0 and 2, with 1 being "reasonable"
    curviness = 0.9


    elements = []
    # NB: svg y-coords start from top! eg (0,1) is 1 unit down from top left corner
    
    # list of coordinates, where the n-th member is a
    # list of Points in the n-th fibre
    coords = []
    for n, [p, l] in enumerate(frobs):
        x_coord = (n+1)*x_spread
        if l == [0]:
            coords.append(ram_coords(
                local_algs, p, x_coord, y_centre, y_spread
            ))
        else:
            coords.append(unram_coords(
                l, x_coord, y_centre, y_spread, col_max
            ))

    # draw Spec Z line at the bottom
    elements.append(
        svg.Line(
            stroke = "black",
            stroke_width = line_thickness,
            x1 = coords[0][0].x, # get starting point of line
            y1 = bottom_line,
            x2 = coords[-1][0].x + x_spread, 
            y2 = bottom_line
        )
    )
    # a dashed line afterwards to signify generic fibre
    for y in (bottom_line, y_centre):
        elements.append(
            svg.Line(
                stroke = "black",
                stroke_width = line_thickness,
                stroke_dasharray = "5",
                x1 = coords[-1][0].x + x_spread,
                y1 = y,
                x2 = coords[-1][0].x + 2*x_spread,
                y2 = y
            )
        )
        elements.append(svg.Text(
            x = width - x_spread,
            y = y,
            dx = 16,
            dy = 4,
            text = '(0)',
            text_anchor = "middle")
                        )

    for n, pts in enumerate(coords):
        # dots on Spec Z
        elements.append(
            svg.Circle(
                cx = pts[0].x,
                cy = bottom_line,
                r = dot_radius,
                fill="black")
        )
        elements.append(
            svg.Text(
                x = pts[0].x,
                y = bottom_line,
                dy = 20,
                text = f'({frobs[n][0]})',
                text_anchor = "middle",
            )
        )
        # draw fibre
        for pt in pts:
            radius = min(dot_radius + ramify_factor*(pt.girth-1), x_spread/3)
            elements.append(
                svg.Circle(
                    cx = pt.x,
                    cy = pt.y,
                    r = radius,
                    fill = pt.color,
                    stroke="black")
            )
    # now draw lines
    for n in range(num_primes):
        for pt_this in coords[n]:
            for pt_next in (coords + [[Point(width-2*x_spread, y_centre)] ])[n + 1]:
                # we control the angle of the curve by adding a control point
                dx = curviness*round((pt_next.x - pt_this.x)/2) 
                elements.append(
                    svg.Path(
                        stroke = "black",
                        stroke_width = line_thickness,
                        fill = "none",
                        d = [
                            svg.M( x = pt_this.x, y = pt_this.y),
                            svg.CubicBezier(
                                x1 = pt_next.x-dx,
                                y1 = pt_this.y,
                                x2 = pt_this.x+dx,
                                y2 = pt_next.y,
                                x = pt_next.x,
                                y = pt_next.y
                            )
                        ]
                    )
                )

    return svg.SVG(
        width=width,
        height=height,
        elements=elements)

            
        

def unram_coords(frob_cycle_list, x_coord, y_centre, spread, col_max):
    """
    Given list of frobenius cycle describing a fixed fibre with no ramification, evenly spread points with associated colors. Returns list of `Point`s.
    """
    # number of points 
    N = sum(l[1] for l in frob_cycle_list)
    if N == 1:
        return [Point(x_coord, y_centre, 1, hsl_color(frob_cycle_list[0][0], col_max))]
    point_list = []
    point_index = 0         # total index of point
    for cyc_len, num_repeats in frob_cycle_list:
        for _ in range(num_repeats):
            y_offset = round(spread*(2*point_index /(N-1) -1))
            point = Point(x_coord, y_centre - y_offset, 1, hsl_color(cyc_len,col_max))
            point_list.append(point)
            point_index += 1
    return point_list


def ram_coords(local_algs, p, x_coord, y_centre, spread):
    """ Given list of strings `local_algs` as stored in the database, and a prime `p`,
    extract the points in the ramified fibre
    """
    algs = []
    for s in local_algs:
        if s[0] == "m":
            s = s[1:]
        if s.split('.')[0] == str(p):
            algs.append(s)

    assert algs != [], f"Ramified prime {p} has no local data!"
    N = len(algs)
    point_list = []
    if N == 1:
        ram_index = int(algs[0].split('.')[1])
        return [Point(x_coord, y_centre, ram_index, "black")]
    
    for point_index, string in enumerate(algs):
        ram_index = int(string.split('.')[1])
        y_offset = round(spread*(2*point_index /(N-1) -1))
        point = Point(x_coord, y_centre - y_offset, ram_index, "black")
        point_list.append(point)
    return point_list

    
def hsl_color(n, n_max):
    """
    Closer to a hard-coded color (teal) from black
    as n gets closer to n_max
    """
    if n_max == 0:
        return "black"
    s_max = 90
    l_max = 90
    s = round(n/n_max*s_max)
    l = round(n/n_max*l_max)
    # l = 73
    return f"hsl(180,{s}%,{l}%)"

### Testing

def test_drawspec():
    frobs = [[2, [0]], [3, [[6, 1], [2, 1]]], [5, [[4, 1], [2, 1], [1, 2]]], [7, [[8, 1]]], [11, [[8, 1]]], [13, [[2, 4]]], [17, [[3, 2], [1, 2]]], [19, [[8, 1]]], [23, [[6, 1], [2, 1]]]]
    local_algs = ['2.2.2.1', '2.6.8.1', '173.2.0.1', '173.2.1.1', '173.2.0.1', '173.2.0.1', 'm16493.1.2.0', 'm16493.1.2.0', 'm16493.1.2.0', 'm16493.2.1.1']

    canvas = draw_spec(frobs, local_algs, True)
    filename = "/tmp/test.svg"
    with open(filename, mode='w') as f:		
        f.write(canvas.as_str())

    print("Saved spectrum to /tmp/test.svg")
    return 0
