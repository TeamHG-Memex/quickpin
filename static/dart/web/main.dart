import 'dart:html';

import 'package:angular/angular.dart';
import 'package:angular/application_factory.dart';
import 'package:bootjack/bootjack.dart';
import 'package:dialog/dialogs/alert.dart';
import 'package:dialog/dialogs/confirm.dart';
import 'package:dquery/dquery.dart';
import 'package:logging/logging.dart';

import 'package:quickpin/authentication.dart';
import 'package:quickpin/component/admin/background_tasks.dart';
import 'package:quickpin/component/admin/configuration.dart';
import 'package:quickpin/component/admin/index.dart';
import 'package:quickpin/component/autocomplete_text.dart';
import 'package:quickpin/component/autocomplete.dart';
import 'package:quickpin/component/breadcrumbs.dart';
import 'package:quickpin/component/busy_button.dart';
import 'package:quickpin/component/d3/grip.dart';
import 'package:quickpin/component/d3/heatmap.dart';
import 'package:quickpin/component/d3/sparkline.dart';
import 'package:quickpin/component/edit_select.dart';
import 'package:quickpin/component/edit_text.dart';
import 'package:quickpin/component/edit_password.dart';
import 'package:quickpin/component/excerpt.dart';
import 'package:quickpin/component/home.dart';
import 'package:quickpin/component/label/list.dart';
import 'package:quickpin/component/login.dart';
import 'package:quickpin/component/markdown.dart';
import 'package:quickpin/component/masonry.dart';
import 'package:quickpin/component/modal.dart';
import 'package:quickpin/component/modal/alert.dart';
import 'package:quickpin/component/modal/form.dart';
import 'package:quickpin/component/nav.dart';
import 'package:quickpin/component/pager.dart';
import 'package:quickpin/component/profile/list.dart';
import 'package:quickpin/component/profile/notes.dart';
import 'package:quickpin/component/profile/posts.dart';
import 'package:quickpin/component/profile/relations.dart';
import 'package:quickpin/component/profile/view.dart';
import 'package:quickpin/component/progress_bar.dart';
import 'package:quickpin/component/search.dart';
import 'package:quickpin/component/title.dart';
import 'package:quickpin/component/user/list.dart';
import 'package:quickpin/component/user/view.dart';
import 'package:quickpin/decorator/current_route.dart';
import 'package:quickpin/formatter/date.dart';
import 'package:quickpin/formatter/default.dart';
import 'package:quickpin/formatter/number.dart';
import 'package:quickpin/rest_api.dart';
import 'package:quickpin/router.dart';
import 'package:quickpin/sse.dart';

/// The main application module.
class QuickPinApplication extends Module {
    QuickPinApplication({Level logLevel: Level.OFF}) {
        Logger.root.level = logLevel;
        Logger.root.onRecord.listen((LogRecord rec) {
            print('${rec.time} [${rec.level.name}] ${rec.message}');
        });

        NodeValidatorBuilder nodeValidator = new NodeValidatorBuilder.common()
            ..allowHtml5()
            ..allowElement('a', attributes: ['href'])
            ..allowElement('i', attributes: ['class'])
            ..allowElement('img', attributes: ['alt', 'src']);

        bind(AdminIndexComponent);
        bind(AuthenticationController);
        bind(AutoCompleteTextComponent);
        bind(AutocompleteComponent);
        bind(BackgroundTasksComponent);
        bind(BreadcrumbsComponent);
        bind(BusyButtonComponent);
        bind(ConfigurationListComponent);
        bind(CurrentRoute);
        bind(DefaultFormatter);
        bind(EditSelectComponent);
        bind(EditTextComponent);
        bind(EditPasswordComponent);
        bind(ExcerptComponent);
        bind(GripComponent);
        bind(HeatmapComponent);
        bind(HomeComponent);
        bind(IsoDateFormatter);
        bind(LabelListComponent);
        bind(LargeNumberFormatter);
        bind(LoginComponent);
        bind(MarkdownComponent);
        bind(MasonryComponent);
        bind(ModalComponent);
        bind(ModalAlertComponent);
        bind(ModalFormComponent);
        bind(NavComponent);
        bind(PagerComponent);
        bind(ProfileComponent);
        bind(ProfileListComponent);
        bind(ProfileNotesComponent);
        bind(ProfilePostsComponent);
        bind(ProfileRelationsComponent);
        bind(ProgressBarComponent);
        bind(NodeValidator, toValue: nodeValidator);
        bind(RestApiController);
        bind(RouteInitializerFn, toImplementation: QuickPinRouteInitializer);
        bind(SearchComponent);
        bind(SparklineComponent);
        bind(SseController);
        bind(TitleService);
        bind(UserComponent);
        bind(UserListComponent);
    }
}

/// The application entry point.
///
/// This instantiates and runs the application.
void main() {
    // Register Bootjack components.
    Collapse.use();
    Dropdown.use();
    Modal.use();
    Transition.use();

    // Create main application.
    applicationFactory()
        .addModule(new QuickPinApplication())
        .run();
}
