import { createApp, onMounted, reactive, ref, watch } from "vue";
import { createVuetify, useTheme } from "vuetify";

// The app's own routes, in the URL fragment: "#/" creates a resource, "#/<id>" edits one; a
// "theme" query there (as "#/1?theme=dark") is the display theme
const route = new URL(location.hash.slice(1) || "/", location.origin);
const resourceId = route.pathname === "/" ? null : Number(route.pathname.slice(1));
const apiUrl = resourceId === null ? "/api/resources/" : `/api/resources/${resourceId}/`;
// Django's CSRF token, from its cookie (which the upload client reads too)
const csrfToken = (await cookieStore.get("csrftoken"))?.value ?? "";

const app = createApp({
  setup() {
    // The theme is switchable, and kept in the route
    const theme = useTheme();
    const dark = ref(route.searchParams.get("theme") === "dark");
    theme.global.name.value = dark.value ? "dark" : "light";
    watch(dark, (value) => {
      theme.global.name.value = value ? "dark" : "light";
      route.searchParams.set("theme", value ? "dark" : "light");
      location.replace(`#${route.pathname}${route.search}`);
    });

    // Each widget's value, bound with v-model; empty means keep any existing file
    const values = reactive({
      s3ff_mandatory_blob: "",
      s3ff_optional_blob: "",
      s3ff_optional_limited_blob: "",
      s3ff_disabled_blob: "",
    });
    // Each existing file's URL, from the API; the widget displays its final component as the name
    const existing = reactive({});
    const errors = reactive({});

    const load = async () => {
      const response = await fetch(apiUrl);
      const resource = await response.json();
      for (const name of Object.keys(values)) {
        existing[name] = resource[name] ?? "";
      }
    };

    const submit = async () => {
      for (const key of Object.keys(errors)) {
        delete errors[key];
      }
      // An empty value means keep, so it needn't be sent; the request is then a partial update
      const payload = Object.fromEntries(Object.entries(values).filter(([, value]) => value !== ""));
      const response = await fetch(apiUrl, {
        method: resourceId === null ? "POST" : "PATCH",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
        body: JSON.stringify(payload),
      });
      if (response.ok) {
        // Show the saved resource, by (re)loading its route
        const resource = await response.json();
        location.hash = `#/${resource.id}${route.search}`;
        location.reload();
      } else if (response.status === 400) {
        Object.assign(errors, await response.json());
      } else {
        errors.non_field_errors = [`${response.status} ${response.statusText}`];
      }
    };

    if (resourceId !== null) {
      // Vue awaits an async hook, so a failure to load is reported through its error handling
      onMounted(load);
    }

    // The other renderings of the same resource, for the toggle
    const plainUrl = resourceId === null ? "/resources/create/" : `/resources/${resourceId}/`;
    const daisyuiUrl = `${plainUrl}daisyui/`;

    return { dark, values, existing, errors, submit, plainUrl, daisyuiUrl };
  },
});
// The widget is a custom element, not a Vue component
app.config.compilerOptions.isCustomElement = (tag) => tag === "s3-file-input";
app.use(createVuetify());
app.mount("#app");
