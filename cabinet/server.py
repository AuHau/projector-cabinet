import uasyncio
import utemplate.recompile
import picoweb
from cabinet import cabinet

app = picoweb.WebApp(__name__)

# TODO: Switch back to `utemplate.source` upon finishing development
app.template_loader = utemplate.recompile.Loader(__name__.split(".", 1)[0], "templates")

@app.route("/")
def homepage(req, resp):
    cab = cabinet.Cabinet()
    data = {}

    if req.method == "POST":
        yield from req.read_form_data()

        if "target" in req.form:
            new_target = int(req.form["target"])

            if new_target > cabinet.ACTUATOR_LENGTH:
                raise ValueError("New target exceeded max. length!")

            print(f"Updating to new target {new_target}mm")
            cab.target = new_target
            data["message"] = "Update successful!"

        if "go" in req.form:
            data["message"] = "Actuator is going for it!"
            print("Triggering actuator")
            uasyncio.run(cab.trigger_move())

    data["current_target"] = cab.target
    yield from picoweb.start_response(resp, content_type="text/html")
    yield from app.render_template(resp, "homepage.tpl", (data,))


def start():
    app.run(debug=True, host="0.0.0.0", port=80)
