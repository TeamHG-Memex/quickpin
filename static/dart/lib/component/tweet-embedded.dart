library tweet_embedded;

import 'package:angular/angular.dart';
import 'dart:js';
import 'dart:async';
import 'dart:html';

@Component(selector: 'tweet-embedded', templateUrl: 'packages/quickpin/component/tweet-embedded.html', cssUrl: 'tweet-embedded.css', useShadowDom: false)
class TweetEmbeddedComponent {
  String screenName;
  Element element;

  @NgAttr('screen-name')
  void set myScreenName(value) {
    this.screenName = value;
    new Future.delayed(new Duration(seconds: 1), initWidget);
  }

  void initWidget() {
    context['twttr']['widgets']['load'].apply([this.element]);
  }

  TweetEmbeddedComponent(this.element) {}
}
