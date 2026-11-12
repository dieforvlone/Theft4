#import <UIKit/UIKit.h>

// Presentation only. The app controller owns preferences and the game runtime.
@interface Theft4LauncherView : UIView
@property(nonatomic, readonly) UILabel *statusLabel;
@property(nonatomic, readonly) UILabel *detailLabel;
@property(nonatomic, readonly) UIButton *startButton;
// Which game to load: 0 = GTA IV (Documents/game), 1 = GTA IV: EFLC
// (Documents/game_eflc). The controller owns the preference and switching.
@property(nonatomic, readonly) UISegmentedControl *gameVersion;
@property(nonatomic, readonly) UIButton *prepareButton;
@property(nonatomic, readonly) UIButton *restartButton;
@property(nonatomic, readonly) UISwitch *showCPUUsage;
@property(nonatomic, readonly) UISwitch *showFPS;
@property(nonatomic, readonly) UISwitch *showFrameTime;
@property(nonatomic, readonly) UISwitch *showControls;
@property(nonatomic, readonly) UISwitch *anisotropicFiltering;
@property(nonatomic, readonly) UISwitch *enhancedOutput;
@property(nonatomic, readonly) UISwitch *fsrBoost;
@property(nonatomic, readonly) UISegmentedControl *renderResolution;
@property(nonatomic, readonly) UISwitch *fsrUpscaling;
@property(nonatomic, readonly) UISlider *sharpening;
@property(nonatomic, readonly) uint32_t renderHeight;
@property(nonatomic, readonly) UISwitch *motionBlur;
@property(nonatomic, readonly) UISwitch *depthOfField;
@property(nonatomic, readonly) UIButton *lowPowerButton;
@property(nonatomic, readonly) UIButton *originalPresetButton;
@property(nonatomic, readonly) UISegmentedControl *shadowQuality;
@property(nonatomic, readonly) UISegmentedControl *drawDistance;
@property(nonatomic, readonly) UISegmentedControl *modelDetail;
@property(nonatomic, readonly) UISegmentedControl *reflectionQuality;
@property(nonatomic, readonly) UISegmentedControl *antiAliasing;
@property(nonatomic, readonly) UISwitch *performanceCapture;
@property(nonatomic, readonly) UISwitch *skipIntro;
@property(nonatomic, readonly) UISwitch *customTimeCycle;
@property(nonatomic, readonly) UISwitch *nativeAspect;
@property(nonatomic, readonly) UISwitch *godMode;
@property(nonatomic, readonly) UISwitch *unlimitedAmmo;
#ifdef THEFT4_BC_TEXTURE_COMPATIBILITY
@property(nonatomic, readonly) UISwitch *astcConversion;
@property(nonatomic, readonly) UIButton *deleteTextureCacheButton;
#endif
@property(nonatomic, readonly) UIButton *downloadLogButton;
@property(nonatomic, readonly) UIButton *exportSavesButton;
@property(nonatomic, readonly) UIButton *importSavesButton;
@property(nonatomic, readonly) UIButton *installEpisodesButton;
@property(nonatomic, readonly) UILabel *episodesStatusLabel;
- (void)refreshConfigurationSummary;
- (void)setActive:(BOOL)active;
- (void)retireScene;
@end
