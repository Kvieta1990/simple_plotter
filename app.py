from flask import \
    Flask, \
    render_template, \
    request, \
    redirect, \
    url_for, \
    flash, \
    session
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import os
import uuid
import numpy as np

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'  # Ensure this directory exists
app.secret_key = '9KiK5EKghVjtkc8rwHMK6DkNhveMDv'


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Handle File Upload
        single_mode = request.form.get('fileMode')
        if single_mode == "single":
            file = request.files['datafile']
            num_header_lines = int(request.form.get('headerlines', 0))
            if file:
                fn_save = str(uuid.uuid4()) + "." + file.filename.split(".")[1]
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], fn_save)
                file.save(filepath)

                session.pop('visited_plot', None)
                session.modified = True

                return redirect(
                    url_for(
                        'plot',
                        filename=fn_save,
                        filename_i=file.filename,
                        headerlines=num_header_lines,
                        col_plot=1,
                        single_mode=1
                    )
                )
        else:
            num_header_lines = int(request.form.get('headerlines', 0))
            col_plot = int(request.form.get('colplot', 1))
            files = request.files.getlist('datafile')
            fn_save = str(uuid.uuid4())
            fns_init = list()
            for i, file in enumerate(files):
                fn_save_f = fn_save + f"_{i + 1}"
                fn_save_f += ("." + file.filename.split(".")[1])
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], fn_save_f)
                file.save(filepath)
                fns_init.append(file.filename)

            multi_fn_tmp = fn_save + "_mfn.tmp"
            with open(
                os.path.join(app.config['UPLOAD_FOLDER'], multi_fn_tmp), "w"
            ) as f:
                for fn_init in fns_init:
                    f.write("{0:s}\n".format(fn_init))

            session.pop('visited_plot', None)
            session.modified = True

            return redirect(
                url_for(
                    'plot',
                    filename=fn_save,
                    filename_i=fn_save,
                    headerlines=num_header_lines,
                    col_plot=col_plot,
                    single_mode=0
                )
            )

    return render_template('index.html')


@app.route('/plot/<filename>/<filename_i>')
def plot(filename, filename_i):
    if 'visited_plot' in session:
        if request.referrer and 'plot' in request.referrer:
            session.pop('visited_plot', None)
            session.modified = True
            return render_template('index.html', redirected=True)

    header_lines = request.args.get('headerlines', default=0, type=int)
    col_plot = request.args.get('col_plot', default=1, type=int)
    smode = request.args.get('single_mode', default=1, type=int)

    print("[Info]", session)

    if 'visited_plot' in session:
        session.pop('visited_plot', None)
        session.modified = True
        return render_template('index.html')

    if smode == 1:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            df = pd.read_csv(
                filepath,
                skiprows=header_lines,
                header=None,
                delimiter=r'\s*,\s*|\s+'
            )
            df.columns = [f'column-{i}' for i in range(len(df.columns))]
        except:  # noqa
            error_message = "File reading error. Please check the number of "
            error_message += "header lines, input it correctly in the box."
            flash(error_message, 'error')
            return redirect(url_for('index'))

        # Remove the uploaded data file after reading, to save space.
        os.remove(filepath)

        df = df.apply(pd.to_numeric, errors='coerce')
        df = df.dropna(axis=1, how='all')

        fig = px.line(
            df,
            x=df.columns[0],
            y=df.columns[1:],
            height=600
        )
        fig.update_layout(
            legend_title='Data',
            height=800
        )
        fig.update_xaxes(title_text='X')
        fig.update_yaxes(title_text='Y')

        plot_html = pio.to_html(fig, full_html=False)

        session['visited_plot'] = True
        session.modified = True

        return render_template('plot.html', plot_html=plot_html, fn=filename_i)
    else:
        fns_init_f = os.path.join(
            app.config['UPLOAD_FOLDER'], filename + "_mfn.tmp"
        )
        with open(fns_init_f, "r") as f:
            lines = f.readlines()

        # After reading, remove the file to save space
        os.remove(fns_init_f)

        all_xs = list()
        all_ys = list()

        fig = go.Figure()
        for i in range(len(lines)):
            filepath = os.path.join(
                app.config['UPLOAD_FOLDER'],
                filename + f"_{i + 1}." + lines[i].strip().split(".")[1]
            )

            try:
                df = pd.read_csv(
                    filepath,
                    skiprows=header_lines,
                    header=None,
                    delimiter=r'\s*,\s*|\s+'
                )
            except:  #noqa
                error_message = "File reading error. Please check the number of "
                error_message += "header lines, input it correctly in the box."
                flash(error_message, 'error')
                return redirect(url_for('index'))

            df = df.apply(pd.to_numeric, errors='coerce')
            df = df.dropna(axis=1, how='all')

            try:
                trace = go.Scatter(
                    x=df.iloc[:, 0],
                    y=df.iloc[:, col_plot],
                    mode='lines',
                    name=lines[i].strip()
                )
            except:  # noqa
                error_message = "Plot error. Please check the number of "
                error_message += "columns in the input data files, input "
                error_message += "a valid column in the box."
                flash(error_message, 'error')
                return redirect(url_for('index'))

            fig.add_trace(trace)

            all_xs.append(df.iloc[:, 0])
            all_ys.append(df.iloc[:, col_plot])

            # Remove uploaded file after plotting to save space
            os.remove(filepath)

        num_values = 10
        yminmin = np.inf
        ymaxmax = -np.inf
        for yl in all_ys:
            ydiff = max(yl) - min(yl)
            if ydiff < yminmin:
                yminmin = ydiff
            if ydiff > ymaxmax:
                ymaxmax = ydiff
        
        scale_u = ymaxmax / yminmin * 1.5
        scale_l = 1. / scale_u
        offset_u = ymaxmax - yminmin
        offset_l = -offset_u

        def update_data_gen(scale, offset, pos):
            tmp = scale * all_ys[pos] + offset
            return [tmp if i == pos else all_ys[i] for i in range(len(all_ys))]
        
        def update_x_gen(offset, pos):
            tmp = all_xs[pos] + offset
            return [tmp if i == pos else all_xs[i] for i in range(len(all_xs))]

        scale_arr = np.linspace(scale_l, scale_u, 20)
        init_idx = np.abs(scale_arr - 1.).argmin()
        scale_arr[init_idx] = 1.
        offset_arr = np.linspace(offset_l, offset_u, 20)
        o_init_idx = np.abs(offset_arr).argmin()
        offset_arr[o_init_idx] = 0.

        if len(all_ys) == 2:
            sliders_list = list()
            for i in range(len(all_ys)):
                sliders_list.append(
                    {
                        "yanchor": "bottom",
                        "xanchor": "left",
                        "pad": {"t": 30},
                        "len": 0.9,
                        "x": 0.1,
                        "y": -0.2 - i * .6 - .1,
                        "currentvalue": {"prefix": f"Scale data-{i + 1}: "},
                        "active": init_idx,
                        "steps": [
                            {
                                "label": "{0:.2e}".format(s),
                                "method": "update",
                                "args": [{"y": update_data_gen(s, 0, i)}]
                            } for s in scale_arr
                        ],
                    }
                )
                sliders_list.append(
                    {
                        "yanchor": "bottom",
                        "xanchor": "left",
                        "pad": {"t": 70},
                        "len": 0.9,
                        "x": 0.1,
                        "y": -0.4 - i * .6 - .1,
                        "currentvalue": {"prefix": f"Offset data-{i + 1}: "},
                        "active": o_init_idx,
                        "steps": [
                            {
                                "label": "{0:.2e}".format(o),
                                "method": "update",
                                "args": [{"y": update_data_gen(1, o, i)}]
                            } for o in offset_arr
                        ],
                    }
                )
                x_int = all_xs[i][1] - all_xs[i][0]
                positive_values = np.linspace(x_int, num_values * x_int, num_values)
                negative_values = np.linspace(-x_int, -num_values * x_int, num_values)[::-1]
                xo_array = np.concatenate((negative_values, [0], positive_values))
                xo_array = np.array(xo_array)
                sliders_list.append(
                    {
                        "yanchor": "bottom",
                        "xanchor": "left",
                        "pad": {"t": 70},
                        "len": 0.9,
                        "x": 0.1,
                        "y": -0.6 - i * .6 - .1,
                        "currentvalue": {"prefix": f"X-Offset data-{i + 1}: "},
                        "active": num_values,
                        "steps": [
                            {
                                "label": "{0:.2e}".format(o),
                                "method": "update",
                                "args": [{"x": update_x_gen(o, 0)}]
                            } for o in xo_array
                        ],
                    }
                )

        if len(all_ys) == 2:
            fig.update_layout(
                legend_title='Data',
                height=1200,
                sliders=sliders_list
            )
        else:
            fig.update_layout(
                legend_title='Data',
                height=800
            )

        fig.update_xaxes(title_text='X')
        fig.update_yaxes(title_text='Y')

        plot_html = pio.to_html(fig, full_html=False)

        session['visited_plot'] = True
        session.modified = True

        if len(all_ys) == 2:
            return render_template(
                'plot_s.html',
                plot_html=plot_html,
                fn="Plot For Multiple Data Files"
            )
        else:
            return render_template(
                'plot.html',
                plot_html=plot_html,
                fn="Plot For Multiple Data Files"
            )


if __name__ == '__main__':
    app.run(debug=True, port=6768)
