import svg
import random

# from dataclasses import dataclass
from sage.all import (sin, cos, arctan2)
# from utils/color import StandardColors

class Point:
    def __init__(self,
                 x: float,
                 y: float,
                 girth:float = 1,
                 color: str = "black",
                 ram_index: int = 1):
        self.x = round(x,3)
        self.y = round(y,3)
        self.girth = girth
        self.color = color
        self.ram_index = ram_index

    def __iter__(self):
        return iter((self.x, self.y))

    def __str__(self):
        return f"Point ({self.x}, {self.y}) of girth {self.girth} and color {self.color}"

    def __add__(self,other):
        return Point(self.x + other.x, self.y + other.y)

        
    def polar_coords(self) -> (float,float):
        r = round((self.x**2 + self.y**2)**0.5, 3)
        theta = arctan2(self.y,self.x)
        return (r,theta)


def draw_spec(frobs, local_alg_dict, colors=True) -> svg.SVG:
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
    # y-coordinate of Spec O_K
    y_centre = round(centre_ratio*height)
    
    line_thickness = 1

    # increase or decrease girth of ramified primes
    ramify_factor = .7
    ram_idx_factor = 2.5

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
                local_alg_dict, p, x_coord, y_centre, y_spread))
        else:
            coords.append(unram_coords(
                l, x_coord, y_centre, y_spread, col_max))

    # draw Spec Z line at the bottom
    elements.append(
        svg.Line(
            stroke = "black",
            stroke_width = line_thickness,
            x1 = coords[0][0].x, # get starting point of line
            y1 = bottom_line,
            x2 = coords[-1][0].x + x_spread, 
            y2 = bottom_line))

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
            text_anchor = "middle"))

    for n, pts in enumerate(coords):
        # dots on Spec Z
        elements.append(
            svg.Circle(
                cx = pts[0].x,
                cy = bottom_line,
                r = dot_radius,
                fill="black"))

        elements.append(
            svg.Text(
                x = pts[0].x,
                y = bottom_line,
                dy = 20,
                text = f'({frobs[n][0]})',
                text_anchor = "middle"))

        # draw fibre
        for pt in pts:
            radius = min(dot_radius + ramify_factor*(pt.girth-1), x_spread/3)
            elements.append(
                svg.Circle(
                    cx = pt.x,
                    cy = pt.y,
                    r = radius,
                    fill = pt.color,
                    stroke="black"))

            for i in range(1,pt.ram_index):
                new_radius = radius + ram_idx_factor*i**(2/3)
                elements.append(
                    svg.Circle(
                        cx = pt.x,
                        cy = pt.y,
                        r = new_radius,
                        fill = "none",
                        stroke = "black",
                        stroke_width = .7))

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
                                y = pt_next.y )]))
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


def ram_coords(local_alg_dict, p, x_coord, y_centre, spread):
    """ Given `local_alg_dict` as defined in web_number_field.py, and a prime `p`,
    extract the points in the ramified fibre
    """
    # list of lists [e,f]
    algs = local_alg_dict[str(p)]

    assert algs != [], f"Ramified prime {p} has no local data!"
    N = len(algs)
    point_list = []
    if N == 1:
        ram_index, residue_deg = algs[0]
        return [Point(x_coord, y_centre, residue_deg, "black", ram_index)]
    
    for point_index, data in enumerate(algs):
        ram_index, residue_deg = data
        y_offset = round(spread*(2*point_index /(N-1) -1))
        point = Point(x_coord, y_centre - y_offset, residue_deg, "black", ram_index)
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

    return f"hsl(180,{s}%,{l}%)"


def draw_gaga(frobs, local_alg_dict, signature, colors=True) -> svg.SVG:
    """ Draw the spectrum of the ring of integers of a number field,
    from data in the lmfdb.
    `frobs` is a list of lists [[p, [frob_cycle1,...,frob_cycleN]]]
    `local_algs` is a list of strings describing ramification behaviour ['p.deg.(other stuff)', ..., ]
    If `colors` is `True`, color classes which lie in the same Frobenius cycle
    """
    # MAYBE: view embeddings as places at oo
    # MAYBE: try spiral


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
    x_spread = 40
    
    # distance between prime ideals in same fibre
    # = total distance from top to bottom
    y_spread = 30

    # (absolute) height of svg
    height = 200

    # (absolute) width of svg
    width = 200

    # fraction of height of centre line around which the primes in spec are centred
    centre_ratio = 1/2
    y_centre = round(centre_ratio*height)
    
    line_thickness = 1

    # increase or decrease girth of ramified primes
    ramify_factor = .7
    ram_idx_factor = 2.5

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
                local_alg_dict, p, x_coord, y_centre, y_spread))
        else:
            coords.append(unram_coords(
                l, x_coord, y_centre, y_spread, col_max))

    for n, pts in enumerate(coords):
        # draw fibre
        for pt in pts:
            radius = min(dot_radius + ramify_factor*(pt.girth-1), x_spread/3)
            elements.append(
                svg.Circle(
                    cx = pt.x,
                    cy = pt.y,
                    r = radius,
                    fill = pt.color,
                    stroke="black"))

            for i in range(1,pt.ram_index):
                new_radius = radius + ram_idx_factor*i**(2/3)
                elements.append(
                    svg.Circle(
                        cx = pt.x,
                        cy = pt.y,
                        r = new_radius,
                        fill = "none",
                        stroke = "black",
                        stroke_width = .7))

    # now draw lines
    for n in range(num_primes-1):
        for pt_this in coords[n]:
            for pt_next in coords[n + 1]:
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
                                y = pt_next.y )]))

    for n, sign in enumerate(signature):
        x = 100
        y = 30 + n*140
        elements.append(
            svg.Circle(
                stroke = "black",
                fill = "none",
                cx = x,
                cy = y,
                r = 20,
                stroke_width = 1.5))
        if sign == 1:
            elements.append(
                svg.Circle(
                    stroke = "black",
                    fill = "black",
                    cx = x,
                    cy = y,
                    r = 2))
        else:
            for m in range(1,sign+1):
                print(m)
                x_new = round(x + 12*cos(2*m*3.1415/sign),3)
                y_new = round(y + 12*sin(2*m*3.1415/sign),3)
                print(x_new, y_new)
                elements.append(
                    svg.Circle(
                        stroke = "black",
                        fill = "black",
                        cx = x_new,
                        cy = y_new,
                        r = 2))

    return svg.SVG(
        width=width,
        height=height,
        elements=elements)

def draw_gaga_spiral(frobs, local_alg_dict, signature, colors=True) -> svg.SVG:
    """ Draw the spectrum of the ring of integers of a number field,
    from data in the lmfdb.
    `frobs` is a list of lists [[p, [frob_cycle1,...,frob_cycleN]]]
    `local_algs` is a list of strings describing ramification behaviour ['p.deg.(other stuff)', ..., ]
    If `colors` is `True`, color classes which lie in the same Frobenius cycle
    """
    # MAYBE: view embeddings as places at oo
    # MAYBE: try spiral

    # will set viewbox centered at (0,0)!

    num_primes = len(frobs)
    num_colors = max(len(l) for _, l in frobs)
    if colors:
        col_max = max(i[0] for [p,l] in frobs for i in l if l != [0])
    else:
        col_max = 0

    # (absolute) height of svg
    height = 200

    # (absolute) width of svg
    width = 200

    line_thickness = 1

    # increase or decrease girth of ramified primes
    ramify_factor = .7
    ram_idx_factor = 2.5

    # radius of (unramified) points
    dot_radius = 2.5

    coords = []

    pi = 3.1415
    x_coord = 0
    y_centre = 10
    y_spread = 5
    x_spread = 0
    for n, [p, l] in enumerate(frobs):
        x_coord = (n+1)*x_spread
        if l == [0]:
            coords.append(ram_coords(
                local_alg_dict, p, x_coord, y_centre, y_spread))
        else:
            coords.append(unram_coords(
                l, x_coord, y_centre, y_spread, col_max))

    elements = []

    # for n, pts in enumerate(coords):
    #     # draw fibre
    #     for pt in pts:
    #         radius = dot_radius + ramify_factor*(pt.girth-1)
    #         x,y = compute_helix_coords(pt, n)
    #         elements.append(
    #             svg.Circle(
    #                 cx = x,
    #                 cy = y,
    #                 r = radius,
    #                 fill = pt.color,
    #                 stroke="black"))

    #         # for i in range(1,pt.ram_index):
    #         #     new_radius = radius + ram_idx_factor*i**(2/3)
    #         #     elements.append(
    #         #         svg.Circle(
    #         #             cx = pt.x,
    #         #             cy = pt.y,
    #         #             r = new_radius,
    #         #             fill = "none",
    #         #             stroke = "black",
    #         #             stroke_width = .7))
    helix_pts = []
    num_pts = 1000
    
    for n in range(num_pts):
        pi = 3.1415
        theta = 6*(2*pi*n)/(num_pts)
        r = (n/(200))**3
        x = r*cos(theta)
        y = r*sin(theta)
        if 5 < r < 80:
            helix_pts.append([x,y])

    elements.append(
        svg.Polyline(
            stroke= "black",
            fill= "none",
            points= helix_pts
        )
    )

    polygon_pts = []
    deg = col_max
    print("deg = ", deg)
    for n in range(deg+1):
        theta = n*2*pi/deg - pi/2
        poly_rad = 95
        polygon_pts.append([poly_rad*cos(theta),poly_rad*sin(theta)])

    elements.append(
        svg.Polyline(
            stroke= "black",
            fill= "none",
            points= polygon_pts
        )
    )
    
    # now draw lines
    # for n in range(num_primes-1):
    #     for pt_this in coords[n]:
    #         hpt_mid = compute_helix_coords(Point(pt_this.x, y_centre), n, shift=True)
            
    #         for pt_next in coords[n + 1]:
    #             # we control the angle of the curve by adding a control point
    #             hpt_this = compute_helix_coords(pt_this, n)
    #             hpt_next = compute_helix_coords(pt_next, n+1)
                
    #             ctrl1, ctrl2 = control_pts(
    #                 hpt_this,
    #                 hpt_next
    #             )
    #             elements.append(
    #                 svg.Path(
    #                     stroke = "black",
    #                     stroke_width = line_thickness,
    #                     fill = "none",
    #                     d = [
                            
    #                         svg.M( x = hpt_this.x, y = hpt_this.y),
    #                         svg.CubicBezier(
    #                             x1 = ctrl1.x,
    #                             y1 = ctrl1.y,
    #                             x2 = ctrl2.x,
    #                             y2 = ctrl2.y,
    #                             x = hpt_next.x,
    #                             y = hpt_next.y)])
    #                 )
    #             # ctrl1, ctrl2 = control_pts(
    #             #     hpt_mid,
    #             #     hpt_next
    #             # )

    #             # elements.append(
    #             #     svg.Path(
    #             #         stroke = "black",
    #             #         stroke_width = line_thickness,
    #             #         fill = "none",
    #             #         d = [
    #             #             svg.M( x = hpt_mid.x, y = hpt_mid.y),
    #             #             svg.CubicBezier(
    #             #                 x1 = ctrl1.x,
    #             #                 y1 = ctrl1.y,
    #             #                 x2 = ctrl2.x,
    #             #                 y2 = ctrl2.y,
    #             #                 x = hpt_next.x,
    #             #                 y = hpt_next.y)])
    #             # )
                
    #             # elements.append(
    #             #     svg.Line(x1 = hpt_this.x, # get starting point of line
    #             #              y1 = hpt_this.y,
    #             #              x2 = hpt_mid.x, 
    #             #              y2 = hpt_mid.y,
    #             #              stroke = "black",
    #             #              stroke_width = line_thickness,
    #             #              )
    #             # )
    #             # elements.append(
    #             #     svg.Line(x1 = hpt_mid.x, # get starting point of line
    #             #              y1 = hpt_mid.y,
    #             #              x2 = hpt_next.x, 
    #             #              y2 = hpt_next.y,
    #             #              stroke = "black",
    #             #              stroke_width = line_thickness,
    #             #              )
    #             # )

    # # for n, sign in enumerate(signature):
    # #     x = 100
    # #     y = 30 + n*140
    # #     elements.append(
    # #         svg.Circle(
    # #             stroke = "black",
    # #             fill = "none",
    # #             cx = x,
    # #             cy = y,
    # #             r = 20,
    # #             stroke_width = 1.5))
    # #     if sign == 1:
    # #         elements.append(
    # #             svg.Circle(
    # #                 stroke = "black",
    # #                 fill = "black",
    # #                 cx = x,
    # #                 cy = y,
    # #                 r = 2))
    # #     else:
    # #         for m in range(1,sign+1):
    # #             print(m)
    # #             x_new = round(x + 12*cos(2*m*3.1415/sign),3)
    # #             y_new = round(y + 12*sin(2*m*3.1415/sign),3)
    # #             print(x_new, y_new)
    # #             elements.append(
    # #                 svg.Circle(
    # #                     stroke = "black",
    # #                     fill = "black",
    # #                     cx = x_new,
    # #                     cy = y_new,
    # #                     r = 2))

    return svg.SVG(
        viewBox=svg.ViewBoxSpec(-height/2, -width/2, height, width),
        elements=elements)

def compute_helix_coords(pt, n, shift=False):
    pi = 3.1415
    k = 5
    theta = (2*pi* ( (n % k)))/k
        
    if shift:
        theta += pi/k

    r = 7*n + pt.y+20
        

    x = r*cos(theta)
    y = r*sin(theta)
    return Point(x,y)

def control_pts(pt_this, pt_next, before=False):
    r_this, theta_this = pt_this.polar_coords()
    r_next, theta_next = pt_next.polar_coords()
    _, theta = (pt_next + pt_this).polar_coords()
    # if theta > 3.1415:
    #     theta = 3.1415 - theta
    print("angle = ", theta)
    eps = 1.1
    r_this *= eps
    r_next *= eps
    return (Point(r_this*cos(theta), r_this*sin(theta)),
            Point(r_next*cos(theta), r_next*sin(theta)))

### Testing

def test_drawspec():
    # spectrum of integers of splitting field of x^7 + 41
    frobs = [[2, [[3, 2], [1, 1]]], [3, [[6, 1], [1, 1]]], [5, [[6, 1], [1, 1]]], [7, [0]], [11, [[3, 2], [1, 1]]], [13, [[2, 3], [1, 1]]], [17, [[6, 1], [1, 1]]], [19, [[6, 1], [1, 1]]], [23, [[3, 2], [1, 1]]], [29, [[1, 7]]], [31, [[6, 1], [1, 1]]], [37, [[3, 2], [1, 1]]], [41, [0]], [43, [[7, 1]]], [47, [[6, 1], [1, 1]]], [53, [[3, 2], [1, 1]]], [59, [[6, 1], [1, 1]]]]
    
    local_algs = {"7": [[7,1]], "41": [[7,1]]}
    
    canvas = draw_spec(frobs, local_algs, True)
    filename = "/tmp/test.svg"
    with open(filename, mode='w') as f:		
        f.write(canvas.as_str())

    print("Saved spectrum to /tmp/test.svg")
    return 0

def draw_lady_gaga(n=1, spiral=False):
    # spectrum of integers of splitting field of x^7 + 41
    if n == 1: 
        frobs = [[2, [[3, 2], [1, 1]]], [3, [[6, 1], [1, 1]]], [5, [[6, 1], [1, 1]]], [7, [0]], [11, [[3, 2], [1, 1]]], [13, [[2, 3], [1, 1]]], [17, [[6, 1], [1, 1]]], [19, [[6, 1], [1, 1]]], [23, [[3, 2], [1, 1]]], [29, [[1, 7]]], [31, [[6, 1], [1, 1]]], [37, [[3, 2], [1, 1]]], [41, [0]], [43, [[7, 1]]], [47, [[6, 1], [1, 1]]], [53, [[3, 2], [1, 1]]], [59, [[6, 1], [1, 1]]]]

        signature = [1,3]
        local_algs = {"7": [[7,1]], "41": [[7,1]]}
    elif n == 2:
        frobs = [[2, [[3, 1]]], [3, [[3, 1]]], [5, [[3, 1]]], [7, [0]], [11, [[3, 1]]], [13, [[1, 3]]], [17, [[3, 1]]], [19, [[3, 1]]], [23, [[3, 1]]], [29, [[1, 3]]], [31, [[3, 1]]], [37, [[3, 1]]], [41, [[1, 3]]], [43, [[1, 3]]], [47, [[3, 1]]], [53, [[3, 1]]], [59, [[3, 1]]]]
        signature = [3,0]
        local_algs = {"7": [[3,1]]}

    if spiral: 
        canvas = draw_gaga_spiral(frobs[:9], local_algs, signature, True)
        filename = "/tmp/gaga-spiral.svg"
        with open(filename, mode='w') as f:		
            f.write(canvas.as_str())
        print("Saved to /tmp/gaga-spiral.svg")
    else:
        canvas = draw_gaga(frobs[:4], local_algs, signature, True)
        filename = "/tmp/gaga.svg"
        with open(filename, mode='w') as f:		
            f.write(canvas.as_str())
        print("Saved to /tmp/gaga.svg")
        
    return 0

def reload_this_file():
    with open('draw_spectrum.py', mode='r') as f:		
        exec(f.read())
    print("Reloaded file")
