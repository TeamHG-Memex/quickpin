import 'package:angular/application_factory.dart';
import 'package:quickpin/app.dart';

void main() {
  applicationFactory().addModule(new QuickPin()).run();
}
