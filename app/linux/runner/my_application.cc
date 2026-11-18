#include "my_application.h"

#include <flutter_linux/flutter_linux.h>
#include <cmath>
#ifdef GDK_WINDOWING_X11
#include <gdk/gdkx.h>
#endif

#include "flutter/generated_plugin_registrant.h"
#include "../../native/desktop_window_size.h"

struct _MyApplication {
  GtkApplication parent_instance;
  char** dart_entrypoint_arguments;
};

G_DEFINE_TYPE(MyApplication, my_application, GTK_TYPE_APPLICATION)

static void desktop_method_cb(FlMethodChannel*, FlMethodCall* call, gpointer user_data) {
  g_autoptr(FlMethodResponse) response = nullptr;
  if (g_strcmp0(fl_method_call_get_name(call), "setupWindow") == 0) {
    FlValue* args = fl_method_call_get_args(call);
    FlValue* flag = args && fl_value_get_type(args) == FL_VALUE_TYPE_MAP ? fl_value_lookup_string(args, "enabled") : nullptr;
    FlValue* height = args && fl_value_get_type(args) == FL_VALUE_TYPE_MAP ? fl_value_lookup_string(args, "height") : nullptr;
    if (!flag || fl_value_get_type(flag) != FL_VALUE_TYPE_BOOL || !height || fl_value_get_type(height) != FL_VALUE_TYPE_INT ||
        fl_value_get_int(height) < 160 || fl_value_get_int(height) > 600) {
      response = FL_METHOD_RESPONSE(fl_method_error_response_new("setup", "Invalid setup dimensions", nullptr));
    } else {
      GtkWidget* window = gtk_widget_get_toplevel(GTK_WIDGET(user_data));
      const bool enabled = fl_value_get_bool(flag);
      auto* previous = static_cast<GdkRectangle*>(g_object_get_data(G_OBJECT(window), "chesspilot-main-size"));
      GdkDisplay* display = gtk_widget_get_display(window);
      GdkMonitor* monitor = gdk_display_get_monitor_at_window(display, gtk_widget_get_window(window));
      GdkRectangle work{0, 0, 1920, 1080};
      if (monitor) gdk_monitor_get_workarea(monitor, &work);
      const int scale = monitor ? gdk_monitor_get_scale_factor(monitor) : 1;
      if (enabled && !previous) {
        previous = g_new0(GdkRectangle, 1);
        gtk_window_get_size(GTK_WINDOW(window), &previous->width, &previous->height);
        gtk_widget_get_size_request(window, &previous->x, &previous->y);
        g_object_set_data_full(G_OBJECT(window), "chesspilot-main-size", previous, g_free);
        gtk_widget_set_size_request(window, 360, 160);
      } else if (!enabled && previous) {
        const auto wanted = fit_desktop_window({previous->width, previous->height, previous->x, previous->y},
                                               work.height * scale, scale, work.width * scale);
        gtk_widget_set_size_request(window, wanted.minimum_width, wanted.minimum_height);
        gtk_window_resize(GTK_WINDOW(window), wanted.width, wanted.height);
        g_object_set_data_full(G_OBJECT(window), "chesspilot-main-size", nullptr, nullptr);
      }
      if (enabled) {
        const auto wanted = desktop_setup_size(work.height * scale, scale, work.width * scale,
                                               static_cast<int>(fl_value_get_int(height)));
        gtk_widget_set_size_request(window, wanted.minimum_width, wanted.minimum_height);
        gtk_window_resize(GTK_WINDOW(window), wanted.width, wanted.height);
      }
      const char* title = enabled ? "Stockfish Downloader" : "ChessPilot";
      gtk_window_set_title(GTK_WINDOW(window), title);
      GtkWidget* bar = gtk_window_get_titlebar(GTK_WINDOW(window));
      if (bar && GTK_IS_HEADER_BAR(bar)) gtk_header_bar_set_title(GTK_HEADER_BAR(bar), title);
      response = FL_METHOD_RESPONSE(fl_method_success_response_new(nullptr));
    }
  } else if (g_strcmp0(fl_method_call_get_name(call), "returnTarget") != 0) {
    response = FL_METHOD_RESPONSE(fl_method_not_implemented_response_new());
  } else {
    g_autoptr(FlValue) value = nullptr;
#ifdef GDK_WINDOWING_X11
    GtkWidget* view = GTK_WIDGET(user_data);
    GtkWidget* window = gtk_widget_get_toplevel(view);
    GdkWindow* native = gtk_widget_get_window(window);
    FlValue* args = fl_method_call_get_args(call);
    FlValue* x = args && fl_value_get_type(args) == FL_VALUE_TYPE_MAP ? fl_value_lookup_string(args, "x") : nullptr;
    FlValue* y = args && fl_value_get_type(args) == FL_VALUE_TYPE_MAP ? fl_value_lookup_string(args, "y") : nullptr;
    if (native && GDK_IS_X11_WINDOW(native) && gtk_widget_get_mapped(window) && x && y &&
        fl_value_get_type(x) == FL_VALUE_TYPE_FLOAT && fl_value_get_type(y) == FL_VALUE_TYPE_FLOAT) {
      const double px = fl_value_get_float(x), py = fl_value_get_float(y);
      if (std::isfinite(px) && std::isfinite(py) && px >= 0 && py >= 0 &&
          px < gtk_widget_get_allocated_width(view) && py < gtk_widget_get_allocated_height(view)) {
        int wx, wy;
        if (gtk_widget_translate_coordinates(view, window, static_cast<int>(px), static_cast<int>(py), &wx, &wy)) {
          const int scale = gtk_widget_get_scale_factor(window);
          value = fl_value_new_map();
          fl_value_set_string_take(value, "window", fl_value_new_int(gdk_x11_window_get_xid(native)));
          fl_value_set_string_take(value, "x", fl_value_new_int(wx * scale));
          fl_value_set_string_take(value, "y", fl_value_new_int(wy * scale));
        }
      }
    }
#endif
    // Wayland does not supply a reliable global position for the app's own surface.
    response = FL_METHOD_RESPONSE(fl_method_success_response_new(value));
  }
  fl_method_call_respond(call, response, nullptr);
}

// Called when first Flutter frame received.
static void first_frame_cb(MyApplication* self, FlView* view) {
  gtk_widget_show(gtk_widget_get_toplevel(GTK_WIDGET(view)));
}

// Implements GApplication::activate.
static void my_application_activate(GApplication* application) {
  MyApplication* self = MY_APPLICATION(application);
  GtkWindow* window =
      GTK_WINDOW(gtk_application_window_new(GTK_APPLICATION(application)));

  // Use a header bar when running in GNOME as this is the common style used
  // by applications and is the setup most users will be using (e.g. Ubuntu
  // desktop).
  // If running on X and not using GNOME then just use a traditional title bar
  // in case the window manager does more exotic layout, e.g. tiling.
  // If running on Wayland assume the header bar will work (may need changing
  // if future cases occur).
  gboolean use_header_bar = TRUE;
#ifdef GDK_WINDOWING_X11
  GdkScreen* screen = gtk_window_get_screen(window);
  if (GDK_IS_X11_SCREEN(screen)) {
    const gchar* wm_name = gdk_x11_screen_get_window_manager_name(screen);
    if (g_strcmp0(wm_name, "GNOME Shell") != 0) {
      use_header_bar = FALSE;
    }
  }
#endif
  if (use_header_bar) {
    GtkHeaderBar* header_bar = GTK_HEADER_BAR(gtk_header_bar_new());
    gtk_widget_show(GTK_WIDGET(header_bar));
    gtk_header_bar_set_title(header_bar, "ChessPilot");
    gtk_header_bar_set_show_close_button(header_bar, TRUE);
    gtk_window_set_titlebar(window, GTK_WIDGET(header_bar));
  } else {
    gtk_window_set_title(window, "ChessPilot");
  }

  GdkDisplay* display = gtk_widget_get_display(GTK_WIDGET(window));
  GdkMonitor* monitor = gdk_display_get_primary_monitor(display);
  if (!monitor) monitor = gdk_display_get_monitor(display, 0);
  GdkRectangle work_area{0, 0, 1920, 1080};
  if (monitor) gdk_monitor_get_workarea(monitor, &work_area);
  const int scale = monitor ? gdk_monitor_get_scale_factor(monitor) : 1;
  const auto metrics = desktop_window_size(work_area.height * scale, scale, work_area.width * scale);
  gtk_window_set_default_size(window, metrics.width, metrics.height);
  gtk_widget_set_size_request(GTK_WIDGET(window), metrics.minimum_width, metrics.minimum_height);
  gtk_window_set_keep_above(window, TRUE);
  g_autofree gchar* executable = g_file_read_link("/proc/self/exe", nullptr);
  if (executable) {
    g_autofree gchar* directory = g_path_get_dirname(executable);
    g_autofree gchar* icon = g_build_filename(directory, "data", "chesspilot.png", nullptr);
    gtk_window_set_icon_from_file(window, icon, nullptr);
  }

  g_autoptr(FlDartProject) project = fl_dart_project_new();
  fl_dart_project_set_dart_entrypoint_arguments(
      project, self->dart_entrypoint_arguments);

  FlView* view = fl_view_new(project);
  GdkRGBA background_color;
  // Background defaults to black, override it here if necessary, e.g. #00000000
  // for transparent.
  gdk_rgba_parse(&background_color, "#000000");
  fl_view_set_background_color(view, &background_color);
  gtk_widget_show(GTK_WIDGET(view));
  gtk_container_add(GTK_CONTAINER(window), GTK_WIDGET(view));

  // Show the window when Flutter renders.
  // Requires the view to be realized so we can start rendering.
  g_signal_connect_swapped(view, "first-frame", G_CALLBACK(first_frame_cb),
                           self);
  gtk_widget_realize(GTK_WIDGET(view));

  fl_register_plugins(FL_PLUGIN_REGISTRY(view));
  g_autoptr(FlStandardMethodCodec) codec = fl_standard_method_codec_new();
  g_autoptr(FlMethodChannel) channel = fl_method_channel_new(
      fl_engine_get_binary_messenger(fl_view_get_engine(view)), "chesspilot/desktop", FL_METHOD_CODEC(codec));
  fl_method_channel_set_method_call_handler(channel, desktop_method_cb, view, nullptr);

  gtk_widget_grab_focus(GTK_WIDGET(view));
}

// Implements GApplication::local_command_line.
static gboolean my_application_local_command_line(GApplication* application,
                                                  gchar*** arguments,
                                                  int* exit_status) {
  MyApplication* self = MY_APPLICATION(application);
  for (gchar** argument = *arguments + 1; *argument != nullptr; ++argument) {
    if (g_strcmp0(*argument, "--help") == 0) {
      g_print("Usage: chesspilot [--help]\nLocal chessboard detection and Stockfish analysis.\n");
      *exit_status = 0;
      return TRUE;
    }
  }
  // Strip out the first argument as it is the binary name.
  self->dart_entrypoint_arguments = g_strdupv(*arguments + 1);

  g_autoptr(GError) error = nullptr;
  if (!g_application_register(application, nullptr, &error)) {
    g_warning("Failed to register: %s", error->message);
    *exit_status = 1;
    return TRUE;
  }

  g_application_activate(application);
  *exit_status = 0;

  return TRUE;
}

// Implements GApplication::startup.
static void my_application_startup(GApplication* application) {
  // MyApplication* self = MY_APPLICATION(object);

  // Perform any actions required at application startup.

  G_APPLICATION_CLASS(my_application_parent_class)->startup(application);
}

// Implements GApplication::shutdown.
static void my_application_shutdown(GApplication* application) {
  // MyApplication* self = MY_APPLICATION(object);

  // Perform any actions required at application shutdown.

  G_APPLICATION_CLASS(my_application_parent_class)->shutdown(application);
}

// Implements GObject::dispose.
static void my_application_dispose(GObject* object) {
  MyApplication* self = MY_APPLICATION(object);
  g_clear_pointer(&self->dart_entrypoint_arguments, g_strfreev);
  G_OBJECT_CLASS(my_application_parent_class)->dispose(object);
}

static void my_application_class_init(MyApplicationClass* klass) {
  G_APPLICATION_CLASS(klass)->activate = my_application_activate;
  G_APPLICATION_CLASS(klass)->local_command_line =
      my_application_local_command_line;
  G_APPLICATION_CLASS(klass)->startup = my_application_startup;
  G_APPLICATION_CLASS(klass)->shutdown = my_application_shutdown;
  G_OBJECT_CLASS(klass)->dispose = my_application_dispose;
}

static void my_application_init(MyApplication* self) {}

MyApplication* my_application_new() {
  // Set the program name to the application ID, which helps various systems
  // like GTK and desktop environments map this running application to its
  // corresponding .desktop file. This ensures better integration by allowing
  // the application to be recognized beyond its binary name.
  g_set_prgname(APPLICATION_ID);

  return MY_APPLICATION(g_object_new(my_application_get_type(),
                                     "application-id", APPLICATION_ID, "flags",
                                     G_APPLICATION_NON_UNIQUE, nullptr));
}
