# 모바일 네이버 로그인 API 가이드

## 개요

모바일 앱에서 네이버 로그인을 구현하기 위한 REST API 엔드포인트입니다.

## API 엔드포인트

### 네이버 로그인 (모바일)

**POST** `/accounts/api/naver/mobile/`

모바일 앱에서 네이버 SDK로 받은 `access_token`을 서버로 전송하여 로그인을 처리합니다.

#### 요청

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "access_token": "네이버에서 받은 access_token"
}
```

#### 응답

**성공 (200 OK):**
```json
{
  "success": true,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "activity_name": "사용자명",
    "profile_image_url": "https://example.com/media/images/userprofile/naver_1.jpg"
  },
  "session_id": "세션_ID",
  "requires_real_name": false
}
```

**실패 (400 Bad Request):**
```json
{
  "success": false,
  "error": "에러 메시지"
}
```

#### 필드 설명

- `success`: 요청 성공 여부 (boolean)
- `user`: 사용자 정보 객체
  - `id`: 사용자 ID
  - `email`: 이메일 주소
  - `activity_name`: 활동명 (닉네임)
  - `profile_image_url`: 프로필 이미지 URL (없으면 null)
- `session_id`: 세션 ID (쿠키로도 전달됨)
- `requires_real_name`: 실명 입력 필요 여부 (boolean)
  - `true`: 실명 입력 페이지로 이동 필요
  - `false`: 정상 로그인 완료

## 모바일 앱 구현 가이드

### iOS (Swift)

```swift
import NaverThirdPartyLogin

class ViewController: UIViewController {
    let loginInstance = NaverThirdPartyLoginConnection.getSharedInstance()
    
    override func viewDidLoad() {
        super.viewDidLoad()
        loginInstance?.delegate = self
    }
    
    @IBAction func naverLogin(_ sender: UIButton) {
        loginInstance?.requestThirdPartyLogin()
    }
}

extension ViewController: NaverThirdPartyLoginConnectionDelegate {
    // 로그인 성공 시 호출
    func oauth20ConnectionDidFinishRequestACTokenWithAuthCode() {
        guard let accessToken = loginInstance?.accessToken else {
            print("Access token not available")
            return
        }
        
        // 서버로 access_token 전송
        let url = URL(string: "https://yourdomain.com/accounts/api/naver/mobile/")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = ["access_token": accessToken]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                print("Error: \(error)")
                return
            }
            
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let success = json["success"] as? Bool,
                  success == true else {
                print("Login failed")
                return
            }
            
            // 세션 쿠키 저장 (URLSession이 자동으로 처리)
            // 사용자 정보 저장
            if let user = json["user"] as? [String: Any] {
                let userId = user["id"] as? Int
                let email = user["email"] as? String
                let activityName = user["activity_name"] as? String
                // 사용자 정보 저장
            }
            
            // 실명 입력 필요 여부 확인
            if let requiresRealName = json["requires_real_name"] as? Bool, requiresRealName {
                // 실명 입력 화면으로 이동
                DispatchQueue.main.async {
                    // 실명 입력 화면으로 이동
                }
            } else {
                // 메인 화면으로 이동
                DispatchQueue.main.async {
                    // 메인 화면으로 이동
                }
            }
        }.resume()
    }
    
    // 로그인 실패 시 호출
    func oauth20ConnectionDidFinishRequestACTokenWithRefreshToken() {
        // 리프레시 토큰으로 재시도
    }
    
    func oauth20ConnectionDidFinishDeleteToken() {
        // 로그아웃 완료
    }
    
    func oauth20Connection(_ oauthConnection: NaverThirdPartyLoginConnection!, didFailWithError error: Error!) {
        print("Naver login error: \(error.localizedDescription)")
    }
}
```

### Android (Kotlin)

```kotlin
import com.nhn.android.naverlogin.OAuthLogin
import com.nhn.android.naverlogin.OAuthLoginHandler
import okhttp3.*
import org.json.JSONObject
import java.io.IOException

class MainActivity : AppCompatActivity() {
    private lateinit var mOAuthLoginInstance: OAuthLogin
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        // 네이버 로그인 초기화
        mOAuthLoginInstance = OAuthLogin.getInstance()
        mOAuthLoginInstance.init(
            this,
            "네이버_클라이언트_ID",
            "네이버_클라이언트_시크릿",
            "네이버_앱_이름"
        )
        
        // 네이버 로그인 버튼 클릭
        naverLoginButton.setOnClickListener {
            mOAuthLoginInstance.startOauthLoginActivity(this, mOAuthLoginHandler)
        }
    }
    
    private val mOAuthLoginHandler = object : OAuthLoginHandler() {
        override fun run(success: Boolean) {
            if (success) {
                val accessToken = mOAuthLoginInstance.accessToken
                
                // 서버로 access_token 전송
                val url = "https://yourdomain.com/accounts/api/naver/mobile/"
                val client = OkHttpClient()
                val json = JSONObject()
                json.put("access_token", accessToken)
                
                val requestBody = json.toString().toRequestBody("application/json".toMediaType())
                val request = Request.Builder()
                    .url(url)
                    .post(requestBody)
                    .build()
                
                client.newCall(request).enqueue(object : Callback {
                    override fun onFailure(call: Call, e: IOException) {
                        Log.e("NaverLogin", "서버 요청 실패", e)
                    }
                    
                    override fun onResponse(call: Call, response: Response) {
                        val responseBody = response.body?.string()
                        val json = JSONObject(responseBody)
                        
                        if (json.getBoolean("success")) {
                            // 세션 쿠키 저장 (OkHttp가 자동으로 처리)
                            // 사용자 정보 저장
                            val user = json.getJSONObject("user")
                            val userId = user.getInt("id")
                            val email = user.getString("email")
                            val activityName = user.getString("activity_name")
                            
                            // 실명 입력 필요 여부 확인
                            val requiresRealName = json.getBoolean("requires_real_name")
                            runOnUiThread {
                                if (requiresRealName) {
                                    // 실명 입력 화면으로 이동
                                    val intent = Intent(this@MainActivity, EnterRealNameActivity::class.java)
                                    startActivity(intent)
                                } else {
                                    // 메인 화면으로 이동
                                    val intent = Intent(this@MainActivity, MainActivity::class.java)
                                    startActivity(intent)
                                }
                            }
                        } else {
                            val error = json.getString("error")
                            Log.e("NaverLogin", "로그인 실패: $error")
                        }
                    }
                })
            } else {
                val errorCode = mOAuthLoginInstance.lastErrorCode
                val errorDesc = mOAuthLoginInstance.lastErrorDescription
                Log.e("NaverLogin", "네이버 로그인 실패: $errorCode - $errorDesc")
            }
        }
    }
}
```

### React Native

```javascript
import NaverLogin from '@react-native-seoul/naver-login';
import AsyncStorage from '@react-native-async-storage/async-storage';

// 네이버 로그인 초기화
const naverLogin = NaverLogin.initialize({
  kConsumerKey: '네이버_클라이언트_ID',
  kConsumerSecret: '네이버_클라이언트_시크릿',
  kServiceAppName: '네이버_앱_이름',
  kServiceAppUrlScheme: '네이버_앱_URL_스킴',
});

// 네이버 로그인 처리
const handleNaverLogin = async () => {
  try {
    const result = await naverLogin.login();
    const accessToken = result.accessToken;
    
    // 서버로 access_token 전송
    const response = await fetch('https://yourdomain.com/accounts/api/naver/mobile/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        access_token: accessToken,
      }),
      credentials: 'include', // 쿠키 포함
    });
    
    const data = await response.json();
    
    if (data.success) {
      // 세션 쿠키는 자동으로 저장됨 (credentials: 'include')
      // 사용자 정보 저장
      await AsyncStorage.setItem('userId', data.user.id.toString());
      await AsyncStorage.setItem('userEmail', data.user.email);
      await AsyncStorage.setItem('activityName', data.user.activity_name);
      
      // 실명 입력 필요 여부 확인
      if (data.requires_real_name) {
        // 실명 입력 화면으로 이동
        navigation.navigate('EnterRealName');
      } else {
        // 메인 화면으로 이동
        navigation.navigate('Home');
      }
    } else {
      console.error('로그인 실패:', data.error);
    }
  } catch (error) {
    console.error('네이버 로그인 오류:', error);
  }
};

// 네이버 로그아웃
const handleNaverLogout = async () => {
  try {
    await naverLogin.logout();
    await AsyncStorage.clear();
  } catch (error) {
    console.error('네이버 로그아웃 오류:', error);
  }
};
```

## 웹 기반 네이버 로그인 (참고)

웹 브라우저에서는 기존 OAuth 2.0 방식의 엔드포인트를 사용합니다:

- **로그인 시작**: `GET /accounts/login/naver/`
- **콜백 처리**: `GET /accounts/naver/`

## 에러 처리

### 일반적인 에러 코드

- **400 Bad Request**: 요청 형식이 잘못되었거나 필수 파라미터가 누락됨
- **500 Internal Server Error**: 서버 내부 오류

### 에러 응답 예시

```json
{
  "success": false,
  "error": "네이버 계정에서 이메일 정보를 제공하지 않았습니다."
}
```

## 네이버 로그인 SDK 설정

### iOS 설정

1. **CocoaPods 설치**
   ```ruby
   pod 'naveridlogin-sdk-ios'
   ```

2. **Info.plist 설정**
   ```xml
   <key>CFBundleURLTypes</key>
   <array>
       <dict>
           <key>CFBundleURLSchemes</key>
           <array>
               <string>네이버_앱_URL_스킴</string>
           </array>
       </dict>
   </array>
   ```

### Android 설정

1. **Gradle 의존성 추가**
   ```gradle
   dependencies {
       implementation 'com.naver.nid:naveridlogin-android-sdk:4.2.6'
   }
   ```

2. **AndroidManifest.xml 설정**
   ```xml
   <activity
       android:name="com.nhn.android.naverlogin.ui.NaverLoginActivity"
       android:screenOrientation="portrait"
       android:exported="true" />
   ```

## 보안 고려사항

1. **HTTPS 사용**: 프로덕션 환경에서는 반드시 HTTPS를 사용하세요.
2. **세션 관리**: 서버에서 세션 쿠키를 발급하므로, 이후 API 요청 시 쿠키를 포함해야 합니다.
3. **토큰 검증**: 서버는 네이버 API를 통해 `access_token`의 유효성을 검증합니다.
4. **클라이언트 시크릿**: 클라이언트 시크릿은 서버에서만 사용하고, 앱에 포함하지 마세요.

## 추가 정보

- 네이버 개발자 센터: https://developers.naver.com/
- 네이버 로그인 가이드: https://developers.naver.com/docs/login/overview/
- iOS SDK 가이드: https://developers.naver.com/docs/login/ios/
- Android SDK 가이드: https://developers.naver.com/docs/login/android/

## 카카오 로그인과의 차이점

1. **SDK 초기화**: 네이버는 클라이언트 ID와 시크릿을 모두 필요로 합니다.
2. **사용자 정보 구조**: 네이버는 `response` 객체 안에 사용자 정보를 반환합니다.
3. **성별 코드**: 네이버는 "M"/"F" 형식을 사용합니다 (카카오는 "male"/"female").
4. **생일 형식**: 네이버는 "MM-DD" 형식을 사용합니다 (카카오는 "MMDD").
