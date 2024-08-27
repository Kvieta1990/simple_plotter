from flask import \
    Flask, \
    render_template, \
    request, \
    redirect, \
    url_for, \
    flash
import pandas as pd
import plotly.express as px
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
        file = request.files['datafile']
        num_header_lines = int(request.form.get('headerlines', 0))
        if file:
            fn_save = str(uuid.uuid4()) + "." + file.filename.split(".")[1]
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], fn_save)
            file.save(filepath)
            return redirect(
                url_for(
                    'plot',
                    filename=fn_save,
                    filename_i=file.filename,
                    headerlines=num_header_lines
                )
            )
    return render_template('index.html')


@app.route('/plot/<filename>/<filename_i>')
def plot(filename, filename_i):
    header_lines = request.args.get('headerlines', default=0, type=int)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Read the data while skipping header lines
    try:
        df = pd.read_csv(
            filepath,
            header=None if header_lines == 0 else header_lines,
            delimiter=r'\s*,\s*|\s+'
        )
        df.columns = [f'column-{i}' for i in range(len(df.columns))]
    except:  # noqa
        error_message = "File reading error. Please check the number of "
        error_message += "header lines, input it correctly in the box."
        flash(error_message, 'error')
        return redirect(url_for('index'))

    df = df.apply(pd.to_numeric, errors='coerce')
    df = df.dropna(axis=1, how='all')

    fig = px.line(
        df,
        x=df.columns[0],
        y=df.columns[1:],
        height=600
    )
    fig.update_layout(legend_title='Data')
    fig.update_xaxes(title_text='X')
    fig.update_yaxes(title_text='Y')

    plot_html = pio.to_html(fig, full_html=False)

    return render_template('plot.html', plot_html=plot_html, fn=filename_i)


if __name__ == '__main__':
    app.run(debug=True, port=6768)
