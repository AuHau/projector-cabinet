import uasyncio
import utemplate.recompile
import picoweb
import machine
from cabinet import cabinet, settings

persisted_settings = settings.PersistentSettings()
app = picoweb.WebApp(__name__)

#  `utemplate.source` package compiles the templates and later on changes are not visible
#  for development there is `utemplate.recompile` package which is more compute and memory intense though
app.template_loader = utemplate.source.Loader(__name__.split(".", 1)[0], "templates")


@app.route("/")
def homepage(req, resp):
    cab = cabinet.Cabinet()
    messages = []

    if req.method == "POST":
        yield from req.read_form_data()

        for config_key, config_value_string in req.form.items():
            try:
                parsed = int(config_value_string)
                setattr(persisted_settings, config_key, parsed)
                print(f"Set {config_key} to value {parsed}")
            except ValueError:
                try:
                    parsed = float(config_value_string.replace(",", "."))
                    setattr(persisted_settings, config_key, parsed)
                    print(f"Set {config_key} to value {parsed}")
                except ValueError:
                    messages.append(("danger", f"Error parsing config key {config_key} with value {config_value_string}"))

        messages.append(("success", "Configuration updated!"))
    else:
        req.parse_qs()

        if "go" in req.form:
            messages.append(("primary", "Actuator is going for it!"))
            print("Triggering actuator")
            uasyncio.create_task(cab.trigger())

        elif "reboot" in req.form:
            messages.append(("warning", "Cabinet is restarting!"))
            yield from picoweb.start_response(resp, content_type="text/html")
            yield from app.render_template(resp, "homepage.tpl", (persisted_settings, messages))
            machine.reset()

    yield from picoweb.start_response(resp, content_type="text/html")
    yield from app.render_template(resp, "homepage.tpl", (persisted_settings, messages))


def start():
    app.run(debug=True, host="0.0.0.0", port=80)
