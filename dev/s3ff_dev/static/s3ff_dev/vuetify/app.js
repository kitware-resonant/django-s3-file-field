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
    // The native file input's File; empty means keep any existing file
    const legacyFile = ref(null);
    // Each existing file's URL, from the API; the widget displays its final component as the name
    const existing = reactive({});
    const errors = reactive({});

    const load = async () => {
      const response = await fetch(apiUrl);
      const resource = await response.json();
      for (const name of [...Object.keys(values), "legacy_optional_blob"]) {
        existing[name] = resource[name] ?? "";
      }
    };

    const submit = async () => {
      for (const key of Object.keys(errors)) {
        delete errors[key];
      }
      // The request is multipart, as the native file input needs; the widgets' values are strings,
      // where an empty value means keep
      const body = new FormData();
      for (const [name, value] of Object.entries(values)) {
        body.append(name, value);
      }
      if (legacyFile.value) {
        body.append("legacy_optional_blob", legacyFile.value);
      }
      const response = await fetch(apiUrl, {
        method: resourceId === null ? "POST" : "PATCH",
        headers: { "X-CSRFToken": csrfToken },
        body,
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

    return { dark, values, legacyFile, existing, errors, submit, plainUrl, daisyuiUrl };
  },
});
// The widget is a custom element, not a Vue component
app.config.compilerOptions.isCustomElement = (tag) => tag === "s3-file-input";
app.use(createVuetify());
app.mount("#app");
