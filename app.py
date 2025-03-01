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
import plotly
import os
import uuid
import numpy as np
import json

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'  # Ensure this directory exists
app.secret_key = '9KiK5EKghVjtkc8rwHMK6DkNhveMDv'


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Handle File Upload
        single_mode = request.form.get('fileMode')
        if single_mode == "single":
            file = request.files['datafile1']
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
            numLocs = int(request.form.get('numFiles'))
            files = list()
            for i in range(numLocs):
                for f_tmp in request.files.getlist(f'datafile{i + 1}'):
                    files.append(f_tmp)
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
            return redirect(url_for('index'))

    header_lines = request.args.get('headerlines', default=0, type=int)
    col_plot = request.args.get('col_plot', default=1, type=int)
    smode = request.args.get('single_mode', default=1, type=int)

    print("[Info]", session)

    def is_monotonic(arr):
        return np.all(np.diff(arr) >= 0) or np.all(np.diff(arr) <= 0)

    if 'visited_plot' in session:
        session.pop('visited_plot', None)
        session.modified = True
        return render_template('index.html', redirected=True)

    if smode == 1:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            # df = pd.read_csv(
            #     filepath,
            #     skiprows=header_lines,
            #     header=None,
            #     delimiter=r'\s*,\s*|\s+'
            # )
            # df.columns = [f'column-{i}' for i in range(len(df.columns))]
            # if df.isnull().values.any():
            #     error_message = "File reading error. Please check the number of "
            #     error_message += "header lines, input it correctly in the box."
            #     flash(error_message, 'error')
            #     return render_template('index.html', redirected=True)
            with open(filepath, "r") as f:
                data = np.loadtxt(
                    (x.replace(',', ' ') for x in f),
                    skiprows=header_lines
                )
            if not is_monotonic(data[:, 0]):
                error_message = "File reading error. Please check the number of "
                error_message += "header lines, input it correctly in the box."
                flash(error_message, 'error')
                return render_template('index.html', redirected=True)
        except:  # noqa
            error_message = "File reading error. Please check the number of "
            error_message += "header lines, input it correctly in the box."
            flash(error_message, 'error')
            return render_template('index.html', redirected=True)

        # Remove the uploaded data file after reading, to save space.
        os.remove(filepath)

        # df = df.apply(pd.to_numeric, errors='coerce')
        # df = df.dropna(axis=1, how='all')

        df_dict = dict()
        for i in range(len(data[0])):
            df_dict[f"column-{i}"] = data[:, i]
        df = pd.DataFrame(df_dict)

        fig = px.line(
            df,
            x=df.columns[0],
            y=df.columns[1:],
            height=800
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
        try:
            with open(fns_init_f, "r") as f:
                lines = f.readlines()
        except:  # noqa
            error_message = "Error occurs while refreshing, possibly due to "
            error_message += "data already deleted."
            flash(error_message, 'error')
            return redirect(url_for('index'))

        try:
            fn_if_only_one = lines[0]
            fn_if_only_one += f" (column-{col_plot})"
        except:  # noqa
            error_message = "Error occurs, possible due to column specification."
            flash(error_message, 'error')
            return render_template('index.html', redirected=True)

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
                # df = pd.read_csv(
                #     filepath,
                #     skiprows=header_lines,
                #     header=None,
                #     delimiter=r'\s*,\s*|\s+'
                # )
                # if df.isnull().values.any():
                #     error_message = "File reading error. Please check the number of "
                #     error_message += "header lines, input it correctly in the box."
                #     flash(error_message, 'error')
                #     return render_template('index.html', redirected=True)
                with open(filepath, "r") as f:
                    data = np.loadtxt(
                        (x.replace(',', ' ') for x in f),
                        skiprows=header_lines
                    )
                if not is_monotonic(data[:, 0]):
                    error_message = "File reading error. Please check the number of "
                    error_message += "header lines, input it correctly in the box."
                    flash(error_message, 'error')
                    return render_template('index.html', redirected=True)
            except:  #noqa
                error_message = "File reading error. Please check the number of "
                error_message += "header lines, input it correctly in the box."
                flash(error_message, 'error')
                return redirect(url_for('index'))

            df_dict = dict()
            for j in range(len(data[0])):
                df_dict[f"column-{j}"] = data[:, j]
            df = pd.DataFrame(df_dict)
            # df = df.apply(pd.to_numeric, errors='coerce')
            # df = df.dropna(axis=1, how='all')

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
        yminmin_o = np.inf
        ymaxmax = -np.inf
        ymaxmax_o = -np.inf
        for yl in all_ys:
            ydiff = max(yl) - min(yl)
            if ydiff < yminmin:
                yminmin = ydiff
            if ydiff > ymaxmax:
                ymaxmax = ydiff
            if min(yl) < yminmin_o:
                yminmin_o = min(yl)
            if max(yl) > ymaxmax_o:
                ymaxmax_o = max(yl)

        scale_u = ymaxmax / yminmin * 1.5
        scale_l = 1. / scale_u
        offset_u = ymaxmax_o - yminmin_o
        offset_l = -offset_u

        scale_arr = np.linspace(scale_l, scale_u, 20)
        init_idx = np.abs(scale_arr - 1.).argmin()
        scale_arr[init_idx] = 1.
        offset_arr = np.linspace(offset_l, offset_u, 20)
        o_init_idx = np.abs(offset_arr).argmin()
        offset_arr[o_init_idx] = 0.

        if len(all_ys) == 2:
            trans_params = [
                scale_u, scale_l,
                offset_u, offset_l,
                all_xs[0][1] - all_xs[0][0],
                all_xs[1][1] - all_xs[1][0]
            ]

            fig.update_layout(
                legend_title='Data',
                height=800
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
            graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

            return render_template(
                'plot_s.html',
                graphJSON=graphJSON,
                initial_x1=json.dumps(all_xs[0].tolist()),
                initial_x2=json.dumps(all_xs[1].tolist()),
                initial_y1=json.dumps(all_ys[0].tolist()),
                initial_y2=json.dumps(all_ys[1].tolist()),
                trans_params=trans_params
            )
        else:
            if len(all_ys) == 1:
                return render_template(
                    'plot.html',
                    plot_html=plot_html,
                    fn=fn_if_only_one
                )
            else:
                return render_template(
                    'plot.html',
                    plot_html=plot_html,
                    fn="Plot For Multiple Data Files"
                )


if __name__ == '__main__':
    app.run(debug=True, port=6768)
