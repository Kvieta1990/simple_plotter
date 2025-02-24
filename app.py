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

            # Remove uploaded file after plotting to save space
            os.remove(filepath)

        fig.update_layout(
            legend_title='Data',
            height=800
        )
        fig.update_xaxes(title_text='X')
        fig.update_yaxes(title_text='Y')

        plot_html = pio.to_html(fig, full_html=False)

        session['visited_plot'] = True
        session.modified = True

        return render_template(
            'plot.html',
            plot_html=plot_html,
            fn="Plot For Multiple Data Files"
        )


if __name__ == '__main__':
    app.run(debug=True, port=6768)
